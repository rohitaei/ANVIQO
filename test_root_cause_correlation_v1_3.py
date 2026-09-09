import root_cause_intelligence as rci


def test_active_event_without_timeline_is_explicitly_undetailed(monkeypatch):
    monkeypatch.setattr(rci, "_events", lambda tag: [])
    monkeypatch.setattr(rci, "_verified_memory", lambda tag: [])
    monkeypatch.setattr(rci, "_health", lambda tag: None)
    monkeypatch.setattr(rci, "_maintenance", lambda tag, query: (None, []))
    monkeypatch.setattr(rci, "_pci_evidence", lambda tag, query: {
        "identity": {"tag": "PT-303"},
        "live": {"tag": "PT-303", "value": 49.17, "state": "CRITICAL", "changed": False,
                 "event_active": True, "mode": "SIMULATION", "source": "PCI DEMO STREAM"},
        "answer": None,
    })
    result = rci.build_root_cause_intelligence("Why is PT-303 abnormal?")
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["correlation"]["status"] == "ACTIVE_EVENT_UNDETAILLED"
    assert result["correlation"]["active_event"]["status"] == "ACTIVE_SIGNAL_ONLY"
    assert "event type/message" in " ".join(result["correlation"]["missing_evidence"])
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False


def test_real_timeline_event_is_returned_without_invention(monkeypatch):
    event = {"timestamp": "2026-09-09T10:00:00", "event_type": "HEALTH_CHANGE",
             "severity": "CRITICAL", "message": "PT-303 health changed to CRITICAL", "data": {"state": "CRITICAL"}}
    monkeypatch.setattr(rci, "_events", lambda tag: [event])
    monkeypatch.setattr(rci, "_verified_memory", lambda tag: [])
    monkeypatch.setattr(rci, "_health", lambda tag: None)
    monkeypatch.setattr(rci, "_maintenance", lambda tag, query: (None, []))
    monkeypatch.setattr(rci, "_pci_evidence", lambda tag, query: {
        "identity": {"tag": "PT-303"},
        "live": {"tag": "PT-303", "value": 49.17, "state": "CRITICAL", "changed": False,
                 "event_active": True, "mode": "SIMULATION", "source": "PCI DEMO STREAM"},
        "answer": None,
    })
    result = rci.build_root_cause_intelligence("Why is PT-303 abnormal?")
    assert result["correlation"]["status"] == "EVENT_AVAILABLE"
    assert result["correlation"]["active_event"]["message"] == event["message"]
    assert result["correlation"]["active_event"]["event_type"] == "HEALTH_CHANGE"


def test_verified_field_history_is_exposed_and_correlated(monkeypatch):
    memory = {"memory_id": "PM-1", "timestamp": "2026-09-08T10:00:00", "event": "PT-303 fault",
              "tag": "PT_303", "source": "technician field report", "verified": True,
              "observation": "Transmitter fault observed", "finding": "Signal fault", "maintenance_action": "Checked transmitter"}
    monkeypatch.setattr(rci, "_events", lambda tag: [])
    monkeypatch.setattr(rci, "_verified_memory", lambda tag: [memory])
    monkeypatch.setattr(rci, "_health", lambda tag: None)
    monkeypatch.setattr(rci, "_maintenance", lambda tag, query: (None, []))
    monkeypatch.setattr(rci, "_pci_evidence", lambda tag, query: {
        "identity": {"tag": "PT-303"}, "live": {"tag": "PT-303", "value": 49.17, "state": "CRITICAL",
        "changed": False, "event_active": True, "mode": "SIMULATION", "source": "PCI DEMO STREAM"}, "answer": None})
    result = rci.build_root_cause_intelligence("Why is PT-303 abnormal?")
    assert result["correlation"]["status"] == "EVENT_AVAILABLE"
    assert result["correlation"]["verified_field_history"][0]["memory_id"] == "PM-1"
    assert result["hypotheses"][0]["hypothesis"] == "sensor / transmitter signal issue"


def test_tag_normalization_and_no_fabricated_cause():
    assert rci.extract_tag("Why is pt_303 abnormal") == "PT-303"
    assert rci._norm_tag("PT 303") == "PT303"
    assert rci._norm_tag("PT-303") == "PT303"
