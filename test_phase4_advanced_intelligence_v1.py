import phase4_advanced_intelligence as p4


def test_energy_requires_real_evidence():
    assert p4.analyze_energy({})["status"] == "INSUFFICIENT_EVIDENCE"
    result = p4.analyze_energy({"energy_kwh": 1200, "production_output": 100, "baseline_energy_intensity": 10})
    assert result["status"] == "AVAILABLE"
    assert result["findings"][0]["value"] == 12.0
    assert result["findings"][0]["deviation_percent"] == 20.0


def test_production_impact_does_not_invent_values():
    assert p4.analyze_production_impact({})["status"] == "INSUFFICIENT_EVIDENCE"
    result = p4.analyze_production_impact({"production_output": 100, "production_at_risk": 15})
    assert result["status"] == "AVAILABLE"
    assert any(x["metric"] == "at_risk_percent" and x["value"] == 15.0 for x in result["findings"])


def test_safety_is_evidence_summary_only():
    assert p4.analyze_safety({})["status"] == "INSUFFICIENT_EVIDENCE"
    result = p4.analyze_safety({"interlock_status": "HEALTHY"})
    assert result["status"] == "AVAILABLE"
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False
    assert result["safety"]["human_decision_required"] is True


def test_maintenance_plan_is_recommendation_only():
    result = p4.build_maintenance_plan({"candidates": [
        {"tag": "PT-303", "risk_score": 90, "criticality": 80, "confidence": 70},
        {"tag": "FT-101", "risk_score": 40, "criticality": 50, "confidence": 80},
    ]})
    assert result["status"] == "AVAILABLE"
    assert result["findings"][0]["tag"] == "PT-303"
    assert result["findings"][0]["recommendation_only"] is True


def test_reliability_uses_verified_history_only():
    result = p4.build_reliability_summary({"prediction_history": [
        {"tag": "PT-303", "verified": True, "outcome": "FAILURE"},
        {"tag": "PT-303", "verified": False, "outcome": "FAILURE"},
        {"tag": "FT-101", "verified": True, "outcome": "NORMAL"},
    ]})
    assert result["status"] == "AVAILABLE"
    assert result["findings"][0]["value"] == 2
    assert result["findings"][1]["value"] == 1
    assert result["findings"][2]["value"]["PT-303"] == 1


def test_snapshot_is_read_only_and_no_fabrication():
    result = p4.build_phase4_snapshot({})
    assert result["phase"] == "PHASE_4"
    assert result["status"] == "READY"
    assert result["safety"]["read_only"] is True
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False
    assert all(v["status"] == "INSUFFICIENT_EVIDENCE" for v in result["domains"].values())
