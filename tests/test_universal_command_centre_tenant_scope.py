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


def test_same_plant_id_isolated_between_organizations_and_cache(monkeypatch):
    """The same plant identifier must never expose another organization's rows."""
    import anvi_universal_command_centre as adapter

    def row(tag, name, source):
        return (
            "INSTRUMENT", tag, name, "AREA-A", "Pressure", "TRANSMITTER",
            tag, "", source, {}, "",
        )

    datasets = {
        ("shared-plant-id", "org-a"): [row("PT-A01", "Org A pressure", "a.xlsx")],
        ("shared-plant-id", "org-b"): [row("PT-B01", "Org B pressure", "b.xlsx")],
    }
    queried = []

    class Cursor:
        def execute(self, sql, params):
            self.params = tuple(params)
            queried.append((sql, self.params))

        def fetchall(self):
            return datasets.get(self.params, [])

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
    monkeypatch.setitem(sys.modules, "anvi_verified_pci_adapter", SimpleNamespace(is_bound=lambda *args: True))
    monkeypatch.setitem(sys.modules, "pci_live_simulator", SimpleNamespace(simulate_point=lambda record: {"state": "HEALTHY", "value": 1, "changed": False, "event_active": False, "timestamp": "test", "source": "TEST SIMULATION"}))
    adapter._TENANT_SNAPSHOT_CACHE.clear()

    app = Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context("/"):
        session["plant_id"] = "shared-plant-id"
        session["organization_id"] = "org-a"
        org_a = adapter._tenant_snapshot("shared-plant-id")

        session["organization_id"] = "org-b"
        org_b = adapter._tenant_snapshot("shared-plant-id")

    assert org_a is not None and org_b is not None
    assert org_a["organization_id"] == "org-a"
    assert org_b["organization_id"] == "org-b"
    assert {point["tag"] for point in org_a["points"]} == {"PT-A01"}
    assert {point["tag"] for point in org_b["points"]} == {"PT-B01"}
    assert "PT-B01" not in {point["tag"] for point in org_a["points"]}
    assert "PT-A01" not in {point["tag"] for point in org_b["points"]}
    assert ("shared-plant-id", "org-a") in adapter._TENANT_SNAPSHOT_CACHE
    assert ("shared-plant-id", "org-b") in adapter._TENANT_SNAPSHOT_CACHE
    assert all("WHERE plant_id=? AND organization_id=?" in sql for sql, _ in queried)
    assert [params for _, params in queried] == [
        ("shared-plant-id", "org-a"),
        ("shared-plant-id", "org-b"),
    ]
    adapter._TENANT_SNAPSHOT_CACHE.clear()
