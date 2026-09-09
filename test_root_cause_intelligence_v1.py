import root_cause_intelligence as rci


def test_rci_no_evidence_is_honest(monkeypatch):
    monkeypatch.setattr(rci, "_events", lambda tag: [])
    monkeypatch.setattr(rci, "_verified_memory", lambda tag: [])
    monkeypatch.setattr(rci, "_health", lambda tag: None)
    monkeypatch.setattr(rci, "_pci_evidence", lambda tag, query: {"identity": None, "live": None, "answer": None})
    monkeypatch.setattr(rci, "_maintenance", lambda tag, query: (None, []))

    result = rci.build_root_cause_intelligence("Why is PT-303 abnormal?", "PT-303")

    assert result["status"] == "NO_EVIDENCE"
    assert result["hypotheses"] == []
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False
    assert result["safety"]["automatic_execution"] is False
    assert result["safety"]["human_decision_required"] is True


def test_rci_uses_explicit_verified_evidence(monkeypatch):
    events = [{
        "timestamp": "2026-09-09T10:00:00",
        "event_type": "FINDING",
        "message": "24V failure and fuse blown found during inspection",
    }]
    memory = [{
        "memory_id": "MEM-1",
        "tag": "PT-303",
        "source": "technician field report",
        "verification_status": "VERIFIED",
        "finding": "Fuse failure confirmed",
    }]

    monkeypatch.setattr(rci, "_events", lambda tag: events)
    monkeypatch.setattr(rci, "_verified_memory", lambda tag: memory)
    monkeypatch.setattr(rci, "_health", lambda tag: {"risk_score": 40, "status": "WATCH"})
    monkeypatch.setattr(rci, "_pci_evidence", lambda tag, query: {"identity": None, "live": None, "answer": None})
    monkeypatch.setattr(rci, "_maintenance", lambda tag, query: (None, []))

    result = rci.build_root_cause_intelligence("Why is PT-303 abnormal?", "PT-303")

    assert result["status"] == "HYPOTHESES_AVAILABLE"
    assert any(h["hypothesis"] == "power-supply issue" for h in result["hypotheses"])
    assert all(h["status"] == "INVESTIGATE" for h in result["hypotheses"])
    assert "not confirmed root causes" in result["conclusion"]


def test_rci_normalizes_legacy_tag_spellings():
    assert rci._norm_tag("PT-303") == "PT303"
    assert rci._norm_tag("PT_303") == "PT303"
    assert rci._norm_tag("PT 303") == "PT303"
    assert rci._norm_tag("PT303") == "PT303"


def test_rci_reports_pci_context_when_other_evidence_is_missing(monkeypatch):
    monkeypatch.setattr(rci, "_events", lambda tag: [])
    monkeypatch.setattr(rci, "_verified_memory", lambda tag: [])
    monkeypatch.setattr(rci, "_health", lambda tag: None)
    monkeypatch.setattr(rci, "_maintenance", lambda tag, query: (None, []))
    monkeypatch.setattr(rci, "_pci_evidence", lambda tag, query: {
        "identity": {"tag": "PT_303", "description": "Pressure transmitter"},
        "live": {"tag": "PT_303", "state": "NORMAL", "value": 1.2},
        "answer": "PCI context available",
    })

    result = rci.build_root_cause_intelligence("Why is PT-303 abnormal?")

    assert result["tag"] == "PT-303"
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["evidence_summary"]["pci_identity_available"] is True
    assert result["evidence_summary"]["pci_live_available"] is True
    assert result["hypotheses"] == []
    assert "not enough explicit failure evidence" in result["conclusion"]


def test_rci_explains_current_live_abnormal_condition_without_inventing_root_cause(monkeypatch):
    monkeypatch.setattr(rci, "_events", lambda tag: [])
    monkeypatch.setattr(rci, "_verified_memory", lambda tag: [])
    monkeypatch.setattr(rci, "_health", lambda tag: None)
    monkeypatch.setattr(rci, "_maintenance", lambda tag, query: (None, []))
    monkeypatch.setattr(rci, "_pci_evidence", lambda tag, query: {
        "identity": {"tag": "PT_303", "description": "Pressure transmitter"},
        "live": {
            "tag": "PT_303", "state": "CRITICAL", "value": 88.4,
            "changed": True, "event_active": True, "mode": "SIMULATION",
            "source": "PCI DEMO STREAM",
        },
        "answer": "PCI context available",
    })

    result = rci.build_root_cause_intelligence("Why is PT-303 abnormal?")

    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["observed_condition"]["live_state"] == "CRITICAL"
    assert result["observed_condition"]["changed"] is True
    assert result["observed_condition"]["event_active"] is True
    assert "current abnormal condition" in result["conclusion"]
    assert "Root cause is not confirmed" in result["conclusion"]
    assert result["hypotheses"] == []
