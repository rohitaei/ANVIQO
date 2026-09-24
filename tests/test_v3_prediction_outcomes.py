from v3.prediction_outcomes import verify_prediction_outcome


def _prediction():
    return {
        "plant_id": "PLANT-A",
        "tag": "PT-303",
        "predicted_state": "DEGRADED",
    }


def test_explicit_matching_outcome_is_verified():
    result = verify_prediction_outcome(
        _prediction(),
        {"plant_id": "PLANT-A", "tag": "PT-303", "actual_state": "DEGRADED"},
    )
    assert result["status"] == "VERIFIED_MATCH"


def test_explicit_mismatch_is_recorded_without_new_prediction_logic():
    result = verify_prediction_outcome(
        _prediction(),
        {"plant_id": "PLANT-A", "tag": "PT-303", "actual_state": "HEALTHY"},
    )
    assert result["status"] == "VERIFIED_MISMATCH"


def test_missing_outcome_is_not_inferred():
    result = verify_prediction_outcome(
        _prediction(),
        {"plant_id": "PLANT-A", "tag": "PT-303"},
    )
    assert result["status"] == "UNVERIFIED"


def test_cross_plant_outcome_is_rejected():
    try:
        verify_prediction_outcome(
            _prediction(),
            {"plant_id": "PLANT-B", "tag": "PT-303", "actual_state": "DEGRADED"},
        )
    except ValueError as exc:
        assert "cross-plant" in str(exc)
    else:
        raise AssertionError("cross-plant outcome must be rejected")


def test_safety_contract():
    result = verify_prediction_outcome(
        _prediction(),
        {"plant_id": "PLANT-A", "tag": "PT-303", "actual_state": "DEGRADED"},
    )
    assert result["safety"] == {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "automatic_action": False,
        "human_decision_required": True,
    }
