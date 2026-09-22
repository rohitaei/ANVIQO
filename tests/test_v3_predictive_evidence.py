from v3.predictive_evidence import validate_prediction_evidence


def test_valid_evidence_window_is_reported_without_prediction():
    result = validate_prediction_evidence(
        "PLANT-A",
        "PT-303",
        [
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-22T10:00:00Z", "value": 10},
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-22T11:00:00Z", "value": 12},
        ],
    )
    assert result["quality"] == "VALID"
    assert result["usable_observation_count"] == 2
    assert result["invalid_observation_count"] == 0
    assert result["span_seconds"] == 3600
    assert result["safety"]["plc_write"] is False


def test_partial_evidence_reports_invalid_rows_without_repairing_them():
    result = validate_prediction_evidence(
        "PLANT-A",
        "PT-303",
        [
            {"timestamp": "2026-09-22T10:00:00Z", "value": 10},
            {"timestamp": "not-a-time", "value": 12},
            {"timestamp": "2026-09-22T12:00:00Z", "value": "not-numeric"},
        ],
    )
    assert result["quality"] == "PARTIAL"
    assert result["usable_observation_count"] == 1
    assert result["invalid_observation_count"] == 2
    assert result["evidence"] == [{"timestamp": "2026-09-22T10:00:00Z", "value": 10}]


def test_cross_plant_evidence_is_rejected():
    try:
        validate_prediction_evidence(
            "PLANT-A",
            "PT-303",
            [{"plant_id": "PLANT-B", "timestamp": "2026-09-22T10:00:00Z", "value": 10}],
        )
    except ValueError as exc:
        assert "cross-plant" in str(exc)
    else:
        raise AssertionError("cross-plant evidence must be rejected")


def test_tag_mismatch_is_rejected():
    try:
        validate_prediction_evidence(
            "PLANT-A",
            "PT-303",
            [{"plant_id": "PLANT-A", "tag": "PT-304", "timestamp": "2026-09-22T10:00:00Z", "value": 10}],
        )
    except ValueError as exc:
        assert "tag mismatch" in str(exc)
    else:
        raise AssertionError("tag mismatch must be rejected")


def test_empty_or_unusable_evidence_is_not_predictive():
    result = validate_prediction_evidence(
        "PLANT-A",
        "PT-303",
        [{"timestamp": "2026-09-22T10:00:00Z", "value": "bad"}],
    )
    assert result["quality"] == "EMPTY"
    assert result["usable_observation_count"] == 0
