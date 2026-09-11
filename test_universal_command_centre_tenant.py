import sys
import types
from contextlib import contextmanager

import pytest
from flask import Flask, session

import anvi_universal_command_centre as adapter


def test_active_tenant_uses_tenant_scoped_knowledge(monkeypatch):
    class Cursor:
        def execute(self, sql, args):
            self.args = args

        def fetchall(self):
            return [
                ("INSTRUMENT", "PT-901", "Reactor Pressure", "AREA-A", "Pressure", "TRANSMITTER", "PT-901", "", "plant.xlsx", {}, ""),
                ("EQUIPMENT", "P-901", "Feed Pump", "AREA-A", "Feed", "PUMP", "", "", "plant.xlsx", {}, ""),
            ]

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return Cursor()

    fake_store = types.ModuleType("anvi_tenant_store")
    fake_store._placeholder = lambda: "%s"
    fake_store._connect = lambda: Conn()

    fake_ingestion = types.ModuleType("anvi_plant_ingestion_runtime")
    fake_ingestion.init_schema = lambda: None

    monkeypatch.setitem(sys.modules, "anvi_tenant_store", fake_store)
    monkeypatch.setitem(sys.modules, "anvi_plant_ingestion_runtime", fake_ingestion)

    app = Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context("/"):
        session["plant_id"] = "plant_new"
        snapshot = adapter._tenant_snapshot("plant_new")

    assert snapshot["plant_id"] == "plant_new"
    assert snapshot["total_io"] == 2
    assert snapshot["mode"] == "ONBOARDING_DATA"
    assert {p["tag"] for p in snapshot["points"]} == {"PT-901", ""}
    assert snapshot["safety"]["plc_write"] is False
    assert snapshot["safety"]["scada_control"] is False


def test_no_tenant_data_falls_back_to_original_getter():
    original = lambda: {"source": "legacy", "total_io": 1064}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(adapter, "_tenant_snapshot", lambda plant_id: None)
        app = Flask(__name__)
        app.secret_key = "test"
        with app.test_request_context("/"):
            session["plant_id"] = ""
            assert adapter.get_live_pci_snapshot(original) == {"source": "legacy", "total_io": 1064}
