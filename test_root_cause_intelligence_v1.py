import root_cause_intelligence as rci


def test_rci_no_evidence_is_honest(monkeypatch):
    monkeypatch.setattr(rci, "_events", lambda tag: [])
    monkeypatch.setattr(rci, "_verified_memory", lambda tag: [])
    monkeypatch.setattr(rci, "_health", lambda tag: None)
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
    monkeypatch.setattr(rci, "_maintenance", lambda tag, query: (None, []))

    result = rci.build_root_cause_intelligence("Why is PT-303 abnormal?", "PT-303")

    assert result["status"] == "HYPOTHESES_AVAILABLE"
    assert any(h["hypothesis"] == "power-supply issue" for h in result["hypotheses"])
    assert all(h["status"] == "INVESTIGATE" for h in result["hypotheses"])
    assert "not confirmed root causes" in result["conclusion"]
