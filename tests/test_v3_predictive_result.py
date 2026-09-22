from v3.predictive_result import validate_prediction_result


def test_result_same_tenant_and_tag_is_valid():
    r = validate_prediction_result(
        "plant-a",
        "PT-303",
        {"plant_id": "plant-a", "tag": "PT-303", "predicted_state": "NORMAL"},
    )
    assert r["status"] == "VALIDATED"
    assert r["safety"]["plc_write"] is False


def test_result_cross_plant_is_rejected():
    try:
        validate_prediction_result(
            "plant-a",
            "PT-303",
            {"plant_id": "plant-b", "tag": "PT-303"},
        )
    except ValueError as exc:
        assert "plant scope" in str(exc)
    else:
        raise AssertionError("cross-plant prediction result accepted")


def test_result_tag_mismatch_is_rejected():
    try:
        validate_prediction_result(
            "plant-a",
            "PT-303",
            {"plant_id": "plant-a", "tag": "PT-304"},
        )
    except ValueError as exc:
        assert "tag mismatch" in str(exc)
    else:
        raise AssertionError("mismatched prediction result accepted")


def test_non_dict_result_is_rejected():
    try:
        validate_prediction_result("plant-a", "PT-303", ["global", "result"])
    except ValueError as exc:
        assert "dictionary" in str(exc)
    else:
        raise AssertionError("non-dict prediction result accepted")
