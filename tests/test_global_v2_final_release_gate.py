from anvi_v2_final_release_gate import final_gate, summary

def test_final_gate_is_valid_and_safe():
    gate = final_gate()
    gate.validate()
    assert gate.safety["read_only"] is True
    assert gate.safety["plc_write"] is False
    assert gate.safety["scada_control"] is False
    assert gate.safety["automatic_authorization"] is False
    assert gate.safety["automatic_execution"] is False
    assert gate.safety["human_decision_required"] is True

def test_final_gate_does_not_fake_external_certification():
    s = summary()
    assert s["release_gate"] == "V2_ENGINEERING_COMPLETE"
    assert s["production_certification"] == "PENDING_EXTERNAL_EVIDENCE"
    assert s["production_deploy"] == "BLOCKED_UNTIL_EXPLICIT_APPROVAL"
