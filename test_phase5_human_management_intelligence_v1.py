from phase5_human_management_intelligence import (
    build_management_brief,
    create_human_action_queue,
    record_human_decision,
)


def test_empty_evidence_is_insufficient():
    result = build_management_brief()
    assert result["management_state"] == "INSUFFICIENT_EVIDENCE"
    assert result["evidence_available"] is False


def test_management_brief_reuses_existing_priority():
    result = build_management_brief(
        executive={
            "plant_situation": "ATTENTION",
            "plant_health": {"status": "DEGRADED", "score": 72},
            "top_equipment_risks": [{
                "equipment": "PT-303",
                "priority": 84,
                "status": "URGENT",
                "reason": "Verified evidence requires review.",
            }],
        }
    )
    assert result["management_state"] == "REVIEW_REQUIRED"
    assert result["top_priorities"][0]["equipment"] == "PT-303"
    assert result["top_priorities"][0]["priority"] == 84


def test_action_queue_never_authorizes_or_executes():
    brief = build_management_brief(
        executive={"top_equipment_risks": [{"equipment": "PT-303", "priority": 80}]}
    )
    result = create_human_action_queue(brief)
    assert result["action_queue"][0]["approval_required"] is True
    assert result["action_queue"][0]["approved"] is False
    assert result["action_queue"][0]["executed"] is False


def test_human_decision_is_record_only():
    action = {"action_id": "A-1", "equipment": "PT-303", "action": "INSPECT"}
    result = record_human_decision(action, "APPROVE", reviewer="HOD", note="Proceed with controlled review")
    assert result["approved"] is True
    assert result["executed"] is False
    assert result["decision_recorded"] is True


def test_invalid_decision_is_rejected():
    result = record_human_decision({}, "EXECUTE")
    assert result["status"] == "ERROR"


def test_safety_boundary_is_fixed():
    result = build_management_brief()
    safety = result["safety_boundary"]
    assert safety["read_only"] is True
    assert safety["plc_write"] is False
    assert safety["scada_control"] is False
    assert safety["automatic_authorization"] is False
    assert safety["automatic_execution"] is False
    assert safety["human_decision_required"] is True
    assert safety["causation_claim"] is False
