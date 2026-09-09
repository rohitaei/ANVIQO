import sys
import types


def _fake_modules(memory=None, events=None, live=None, health=None):
    pci = types.ModuleType("pci_conversation")
    pci.find_tag = lambda tag: {"tag": "PT-303", "name": "Test PT"} if tag.replace("_", "-").replace(" ", "-") == "PT-303" else None
    pci.get_live_pci_snapshot = lambda: {"points": [live]} if live else {"points": []}

    pm = types.ModuleType("plant_memory")
    pm.search_all_memory = lambda **kwargs: memory or []

    et = types.ModuleType("event_timeline")
    et.get_events = lambda tag: events or []

    eh = types.ModuleType("equipment_health")
    eh.get_latest_health = lambda tag: health
    return {"pci_conversation": pci, "plant_memory": pm, "event_timeline": et, "equipment_health": eh}


def test_single_live_value_never_becomes_prediction(monkeypatch):
    from failure_prediction import build_failure_prediction
    live = {"tag": "PT-303", "state": "CRITICAL", "value": 49.17, "changed": False, "event_active": True, "mode": "SIMULATION", "source": "PCI_SIMULATION"}
    for name, module in _fake_modules(live=live).items():
        monkeypatch.setitem(sys.modules, name, module)
    result = build_failure_prediction("Predict PT-303 failure risk")
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["trend"]["status"] == "UNAVAILABLE"
    assert result["risk_signal"] == "UNAVAILABLE"
    assert "single live value" in result["reasoning"]
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False
    assert result["decision_status"] == "HUMAN_DECISION_REQUIRED"


def test_two_timestamped_history_points_enable_conditional_prediction(monkeypatch):
    from failure_prediction import build_failure_prediction
    memory = [
        {"tag":"PT-303", "source":"technician field report", "verified":True, "timestamp":"2026-09-01T10:00:00Z", "value":40},
        {"tag":"PT-303", "source":"technician field report", "verified":True, "timestamp":"2026-09-08T10:00:00Z", "value":49},
    ]
    live = {"tag":"PT-303", "state":"CRITICAL", "value":49, "changed":False, "event_active":True, "mode":"SIMULATION", "source":"PCI_SIMULATION", "timestamp":"2026-09-09T10:00:00Z"}
    for name, module in _fake_modules(memory=memory, live=live).items():
        monkeypatch.setitem(sys.modules, name, module)
    result = build_failure_prediction("Predict PT-303 failure risk")
    assert result["status"] == "PREDICTION_AVAILABLE"
    assert result["trend"]["status"] == "AVAILABLE"
    assert result["trend"]["direction"] == "RISING"
    assert result["risk_signal"] == "TREND_RISING"
    assert "probability" not in result["prediction"].lower()
    assert "future failure" not in result["prediction"].lower() or "not a confirmed future failure" in result["prediction"].lower()


def test_detector_requires_equipment_tag_and_prediction_intent():
    from failure_prediction import is_failure_prediction_query
    assert is_failure_prediction_query("Predict PT-303 failure risk")
    assert is_failure_prediction_query("Is PT303 likely to fail?")
    assert not is_failure_prediction_query("Predict the plant")
    assert not is_failure_prediction_query("What is PT-303?")
