import sys
import types

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


def test_two_plants_never_leak_command_centre_data(monkeypatch):
    datasets = {
        "plant_a": [("INSTRUMENT", "PT-A01", "Plant A Pressure", "AREA-A", "Pressure", "TRANSMITTER", "PT-A01", "", "a.xlsx", {}, "")],
        "plant_b": [("INSTRUMENT", "PT-B01", "Plant B Pressure", "AREA-B", "Pressure", "TRANSMITTER", "PT-B01", "", "b.xlsx", {}, "")],
    }

    class Cursor:
        def execute(self, sql, args):
            self.args = args

        def fetchall(self):
            return datasets[self.args[0]]

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
        session["plant_id"] = "plant_a"
        a = adapter.get_live_pci_snapshot(lambda: {"source": "legacy"})
        session["plant_id"] = "plant_b"
        b = adapter.get_live_pci_snapshot(lambda: {"source": "legacy"})

    assert a["plant_id"] == "plant_a"
    assert b["plant_id"] == "plant_b"
    assert {p["tag"] for p in a["points"]} == {"PT-A01"}
    assert {p["tag"] for p in b["points"]} == {"PT-B01"}
    assert "PT-B01" not in {p["tag"] for p in a["points"]}
    assert "PT-A01" not in {p["tag"] for p in b["points"]}


def test_active_tenant_with_no_data_never_falls_back_to_original_getter():
    original = lambda: {"source": "legacy", "total_io": 1064}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(adapter, "_tenant_snapshot", lambda plant_id: None)
        app = Flask(__name__)
        app.secret_key = "test"
        with app.test_request_context("/"):
            session["plant_id"] = "plant-empty"
            snapshot = adapter.get_live_pci_snapshot(original)

    assert snapshot["plant_id"] == "plant-empty"
    assert snapshot["status"] == "NO DATA"
    assert snapshot["total_io"] == 0


def test_no_tenant_data_falls_back_to_original_getter():
    original = lambda: {"source": "legacy", "total_io": 1064}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(adapter, "_tenant_snapshot", lambda plant_id: None)
        app = Flask(__name__)
        app.secret_key = "test"
        with app.test_request_context("/"):
            session["plant_id"] = ""
            assert adapter.get_live_pci_snapshot(original) == {"source": "legacy", "total_io": 1064}



def test_simulation_snapshot_is_stable_across_adjacent_selected_plant_reads(monkeypatch):
    rows = [
        ("INSTRUMENT", "PT-SIM-01", "Test Pressure", "AREA-SIM", "Pressure",
         "TRANSMITTER", "PT-SIM-01", "", "sim.xlsx", {"io_type": "AI"}, "")
    ]

    class Cursor:
        def execute(self, sql, args):
            self.args = args

        def fetchall(self):
            return rows

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
    fake_adapter = types.ModuleType("anvi_verified_pci_adapter")
    fake_adapter.is_bound = lambda plant_id, organization_id=None: True

    calls = {"count": 0}
    fake_simulator = types.ModuleType("pci_live_simulator")

    def simulate_point(record):
        calls["count"] += 1
        state = "CRITICAL" if calls["count"] == 1 else "HEALTHY"
        return {
            "state": state, "value": calls["count"], "changed": False,
            "event_active": False, "timestamp": str(calls["count"]),
            "source": "PCI DEMO STREAM",
        }

    fake_simulator.simulate_point = simulate_point
    monkeypatch.setitem(sys.modules, "anvi_tenant_store", fake_store)
    monkeypatch.setitem(sys.modules, "anvi_plant_ingestion_runtime", fake_ingestion)
    monkeypatch.setitem(sys.modules, "anvi_verified_pci_adapter", fake_adapter)
    monkeypatch.setitem(sys.modules, "pci_live_simulator", fake_simulator)
    adapter._TENANT_SNAPSHOT_CACHE.clear()

    app = Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context("/"):
        session["plant_id"] = "plant_sim"
        session["organization_id"] = "org_sim"
        first = adapter._tenant_snapshot("plant_sim")
        second = adapter._tenant_snapshot("plant_sim")

    assert calls["count"] == 1
    assert first is second
    assert first["critical"] == second["critical"] == 1
    assert first["points"][0]["value"] == second["points"][0]["value"] == 1
    assert first["plant_id"] == second["plant_id"] == "plant_sim"
    assert first["plc_write"] is False
    assert first["scada_control"] is False
