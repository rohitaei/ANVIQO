import sys
import types


def _fake_modules(memory=None, events=None, live=None, health=None, history=None):
    pci = types.ModuleType("pci_conversation")
    pci.find_tag = lambda tag: {"tag": "PT-303", "name": "Test PT"} if tag.replace("_", "-").replace(" ", "-") == "PT-303" else None
    pci.get_live_pci_snapshot = lambda: {"points": [live]} if live else {"points": []}

    pm = types.ModuleType("plant_memory")
    pm.search_all_memory = lambda **kwargs: memory or []

    et = types.ModuleType("event_timeline")
    et.get_events = lambda tag: events or []

    eh = types.ModuleType("equipment_health")
    eh.get_latest_health = lambda tag: health

    ph = types.ModuleType("failure_prediction_history")
    ph.get_observations = lambda tag, limit=500: history or []
    return {"pci_conversation": pci, "plant_memory": pm, "event_timeline": et, "equipment_health": eh, "failure_prediction_history": ph}


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


def test_persisted_plant_history_enables_conditional_prediction(monkeypatch):
    from failure_prediction import build_failure_prediction
    history = [
        {"observation_id":"FPO-1", "tag":"PT-303", "value":40.0, "timestamp":"2026-09-01T10:00:00+00:00", "source":"read-only telemetry", "simulation":False},
        {"observation_id":"FPO-2", "tag":"PT-303", "value":49.0, "timestamp":"2026-09-08T10:00:00+00:00", "source":"read-only telemetry", "simulation":False},
    ]
    live = {"tag":"PT-303", "state":"CRITICAL", "value":49.0, "changed":False, "event_active":True, "mode":"SIMULATION", "source":"PCI_SIMULATION", "timestamp":"2026-09-09T10:00:00Z"}
    for name, module in _fake_modules(live=live, history=history).items():
        monkeypatch.setitem(sys.modules, name, module)
    result = build_failure_prediction("Predict PT-303 failure risk")
    assert result["prediction_version"] == "ANVIQO-FP-V1.1"
    assert result["status"] == "PREDICTION_AVAILABLE"
    assert result["trend"]["direction"] == "RISING"
    assert result["evidence_summary"]["persisted_observation_count"] == 2
    assert "probability" not in result["prediction"].lower()


def test_single_live_value_and_no_history_remain_unavailable(monkeypatch):
    from failure_prediction import build_failure_prediction
    live = {"tag": "PT-303", "state": "CRITICAL", "value": 49.17, "changed": False, "event_active": True, "mode": "SIMULATION", "source": "PCI_SIMULATION"}
    for name, module in _fake_modules(live=live).items():
        monkeypatch.setitem(sys.modules, name, module)
    result = build_failure_prediction("Predict PT-303 failure risk")
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["trend"]["observations_used"] == 0


def test_detector_requires_equipment_tag_and_prediction_intent():
    from failure_prediction import is_failure_prediction_query
    assert is_failure_prediction_query("Predict PT-303 failure risk")
    assert is_failure_prediction_query("Is PT303 likely to fail?")
    assert not is_failure_prediction_query("Predict the plant")
    assert not is_failure_prediction_query("What is PT-303?")


def test_detector_accepts_non_pci_tag_family():
    from failure_prediction import is_failure_prediction_query, extract_tag
    assert extract_tag("Predict TIC_101A failure risk") == "TIC-101A"
    assert is_failure_prediction_query("Predict TIC_101A failure risk")


def test_authenticated_tenant_never_reads_global_prediction_sources(monkeypatch):
    import failure_prediction as fp

    monkeypatch.setattr(fp, "_authenticated_tenant", lambda: ("plant-b", "org-b"))
    monkeypatch.setattr(fp, "_tenant_rows", lambda tag, plant_id: [])
    monkeypatch.setattr(fp, "_pci", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("global PCI path used")))
    monkeypatch.setattr(fp, "_history", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("global history path used")))
    monkeypatch.setattr(fp, "_memory", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("global memory path used")))
    monkeypatch.setattr(fp, "_events", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("global events path used")))
    monkeypatch.setattr(fp, "_health", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("global health path used")))

    result = fp.build_failure_prediction("Predict TIC_101A failure risk")
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["evidence_summary"]["pci_identity_available"] is False
    assert result["safety"]["plc_write"] is False
    assert result["decision_status"] == "HUMAN_DECISION_REQUIRED"
