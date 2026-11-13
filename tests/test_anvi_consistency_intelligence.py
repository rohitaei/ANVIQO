from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def _load_audit():
    spec = importlib.util.spec_from_file_location("anvi_consistency_intelligence", ROOT / "anvi_consistency_intelligence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_consistency_audit_reconciles_snapshot_counts():
    result = _load_audit().audit_snapshot({
        "snapshot_id": "test-1", "timestamp": "2026-11-14T00:00:00+00:00",
        "mode": "SIMULATION", "source": "PCI DEMO STREAM",
        "points": [
            {"state": "HEALTHY", "changed": False, "event_active": False},
            {"state": "WARNING", "changed": True, "event_active": True},
            {"state": "CRITICAL", "changed": False, "event_active": True},
        ],
        "total_io": 3, "healthy": 1, "warning": 1, "critical": 1,
        "changed": 1, "active_events": 2, "areas": [{"total": 3}],
        "plant_health_score": 50.0,
    })
    assert result["status"] == "CONSISTENT"
    assert result["counts"]["total_io"] == 3
    assert result["plant_health_score"] == 50.0
    assert result["plc_write"] is False and result["scada_control"] is False


def test_consistency_audit_flags_conflicting_counts_and_score():
    result = _load_audit().audit_snapshot({
        "points": [{"state": "HEALTHY", "changed": False, "event_active": False}],
        "total_io": 99, "healthy": 99, "warning": 0, "critical": 0,
        "changed": 7, "active_events": 0, "areas": [{"total": 1}],
        "plant_health_score": 1.0,
    })
    assert result["status"] == "INCONSISTENT"
    assert "total_io" in result["mismatches"]
    assert "plant_health_score" in result["mismatches"]


def test_simulator_declares_stable_observation_window():
    source = (ROOT / "pci_live_simulator.py").read_text(encoding="utf-8")
    assert "_SNAPSHOT_CACHE_TTL = 60.0" in source
    assert 'snapshot_id": f"PCI-DEMO-{window}"' in source
    assert "random.Random(20260813 + window)" in source


def test_consistency_endpoint_is_read_only_and_tenant_scoped():
    source = (ROOT / "anviqo_api.py").read_text(encoding="utf-8")
    assert '/api/intelligence/consistency' in source
    assert 'SELECTED_PLANT_ONLY' in source
    assert 'ANVIQO_SIMULATION_PLANT_SLUG' in source

def test_simulator_produces_repeatable_evidence_within_same_minute(monkeypatch):
    spec = importlib.util.spec_from_file_location("pci_live_simulator_test", ROOT / "pci_live_simulator.py")
    simulator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(simulator)
    monkeypatch.setattr(simulator.time, "time", lambda: 1794614400.0)
    first = simulator.simulate_snapshot()
    second = simulator.simulate_snapshot()
    assert first["snapshot_id"] == second["snapshot_id"]
    assert first["timestamp"] == second["timestamp"]
    assert first["healthy"] == second["healthy"]
    assert first["warning"] == second["warning"]
    assert first["critical"] == second["critical"]
    assert [(p["tag"], p["value"], p["state"]) for p in first["points"]] == [
        (p["tag"], p["value"], p["state"]) for p in second["points"]
    ]
