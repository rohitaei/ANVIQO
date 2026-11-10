"""Regression tests for strict organization + plant scoping in Command Centre snapshots."""
import json
import sys
from contextlib import contextmanager
from types import SimpleNamespace

from flask import Flask, session


def test_tenant_snapshot_requires_organization_context(monkeypatch):
    import anvi_universal_command_centre as adapter

    app = Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context("/"):
        session["plant_id"] = "plant-a"
        session.pop("organization_id", None)
        assert adapter._tenant_snapshot("plant-a") is None


def test_tenant_snapshot_query_filters_by_organization_and_plant(monkeypatch):
    import anvi_universal_command_centre as adapter

    captured = {}
    row = (
        "INSTRUMENT", "PT_303", "PT303 Mill outlet Gas Pr", "VRM / MILL",
        "Mill outlet Gas Pr", "AI (4-20mA)", "PT_303", "", 
        "PCI UPDATED DRAWING.xlsx", json.dumps({"criticality": "HIGH"}), "",
    )

    class Cursor:
        def execute(self, sql, params):
            captured["sql"] = sql
            captured["params"] = tuple(params)

        def fetchall(self):
            return [row]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return Cursor()

    class Store:
        @staticmethod
        def _placeholder():
            return "?"

        @staticmethod
        @contextmanager
        def _connect():
            yield Connection()

    monkeypatch.setitem(sys.modules, "anvi_plant_ingestion_runtime", SimpleNamespace(init_schema=lambda: None))
    monkeypatch.setitem(sys.modules, "anvi_tenant_store", Store)
    monkeypatch.setitem(sys.modules, "anvi_verified_pci_adapter", SimpleNamespace(is_bound=lambda *args: False))
    adapter._TENANT_SNAPSHOT_CACHE.clear()

    app = Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context("/"):
        session["plant_id"] = "plant-a"
        session["organization_id"] = "org-a"
        result = adapter._tenant_snapshot("plant-a")

    assert result is not None
    assert result["plant_id"] == "plant-a"
    assert result["organization_id"] == "org-a"
    assert len(result["points"]) == 1
    assert "WHERE plant_id=? AND organization_id=?" in captured["sql"]
    assert captured["params"] == ("plant-a", "org-a")
    assert result["read_only"] is True
    assert result["plc_write"] is False
    assert result["scada_control"] is False
    adapter._TENANT_SNAPSHOT_CACHE.clear()


def test_missing_organization_context_never_falls_back_to_global_simulator():
    import anvi_universal_command_centre as adapter

    app = Flask(__name__)
    app.secret_key = "test"
    called = []
    with app.test_request_context("/"):
        session["plant_id"] = "plant-a"
        session.pop("organization_id", None)
        result = adapter.get_live_pci_snapshot(lambda: called.append(True) or {"source": "GLOBAL_DEMO"})
    assert result["status"] == "NO DATA"
    assert result["plant_id"] == "plant-a"
    assert result["points"] == []
    assert called == []
    assert result["plc_write"] is False
    assert result["scada_control"] is False
