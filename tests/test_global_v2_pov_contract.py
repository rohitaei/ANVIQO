from anvi_v2_pov_contract import REQUIRED_GATES, SAFETY, assert_safe, pov_gate_status


def test_pov_is_pending_without_external_evidence():
    result = pov_gate_status({})
    assert result["pov_ready"] is False
    assert result["production_deploy"] == "BLOCKED_UNTIL_EXPLICIT_APPROVAL"
    assert len(result["gates"]) == len(REQUIRED_GATES)


def test_pov_requires_all_external_gates():
    evidence = {name: True for name in REQUIRED_GATES}
    result = pov_gate_status(evidence)
    assert result["pov_ready"] is True
    assert result["production_deploy"] == "REQUIRES_EXTERNAL_CERTIFICATION_AND_APPROVAL"


def test_pov_safety_contract():
    assert_safe()
    assert SAFETY["read_only"] is True
    assert SAFETY["plc_write"] is False
    assert SAFETY["scada_control"] is False
    assert SAFETY["automatic_authorization"] is False
    assert SAFETY["automatic_execution"] is False
    assert SAFETY["human_decision_required"] is True
