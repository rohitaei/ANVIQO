from v3.predictive_flow import run_predictive_flow


def _observations():
    return [
        {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0},
        {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:01:00Z", "value": 10.2},
    ]


def _predictor(*, plant_id, tag, evidence):
    return {
        "plant_id": plant_id,
        "tag": tag,
        "predicted_state": "NORMAL",
    }


def test_predictive_flow_invokes_only_tenant_aware_predictor():
    calls = []

    def predictor(*, plant_id, tag, evidence):
        calls.append((plant_id, tag, len(evidence)))
        return _predictor(plant_id=plant_id, tag=tag, evidence=evidence)

    result = run_predictive_flow(
        "PLANT-A", "PT-303", _observations(), predictor=predictor
    )

    assert result["status"] == "INVOKED"
    assert result["prediction"]["result"]["plant_id"] == "PLANT-A"
    assert calls == [("PLANT-A", "PT-303", 2)]
    assert result["outcome_verification"]["status"] == "NOT_PROVIDED"
    assert result["evidence"]["quality"] == "VALID"
    assert result["evidence"]["usable_observation_count"] == 2
    assert result["evidence"]["timestamp_start"] == "2026-09-20T10:00:00Z"
    assert result["evidence"]["timestamp_end"] == "2026-09-20T10:01:00Z"
    assert result["evidence"]["span_seconds"] == 60.0
    assert result["safety"]["read_only"] is True
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False


def test_predictive_flow_does_not_invoke_predictor_with_insufficient_evidence():
    calls = []

    def predictor(*, plant_id, tag, evidence):
        calls.append(True)
        return _predictor(plant_id=plant_id, tag=tag, evidence=evidence)

    result = run_predictive_flow(
        "PLANT-A",
        "PT-303",
        [{"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0}],
        predictor=predictor,
    )

    assert result["status"] == "NOT_INVOKED"
    assert result["outcome_verification"]["status"] == "NOT_PROVIDED"
    assert calls == []


def test_predictive_flow_rejects_cross_plant_evidence():
    try:
        run_predictive_flow(
            "PLANT-A",
            "PT-303",
            [{"plant_id": "PLANT-B", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0}],
        )
    except ValueError as exc:
        assert "cross-plant" in str(exc)
    else:
        raise AssertionError("cross-plant evidence was not rejected")


def test_predictive_flow_blocks_legacy_predictor():
    def legacy_predictor(*, tag, evidence):
        return {"plant_id": "PLANT-A", "tag": tag}

    result = run_predictive_flow(
        "PLANT-A", "PT-303", _observations(), predictor=legacy_predictor
    )

    assert result["status"] == "NOT_INVOKED"
    assert "legacy/global" in result["prediction"]["reason"]


def test_predictive_flow_reuses_existing_outcome_verification():
    result = run_predictive_flow(
        "PLANT-A",
        "PT-303",
        _observations(),
        predictor=_predictor,
        outcome={
            "plant_id": "PLANT-A",
            "tag": "PT-303",
            "actual_state": "NORMAL",
        },
    )

    assert result["status"] == "INVOKED"
    assert result["outcome_verification"]["status"] == "VERIFIED_MATCH"
    assert result["outcome_verification"]["plant_id"] == "PLANT-A"
    assert result["outcome_verification"]["tag"] == "PT-303"


def test_predictive_flow_records_explicit_outcome_mismatch_without_inference():
    result = run_predictive_flow(
        "PLANT-A",
        "PT-303",
        _observations(),
        predictor=_predictor,
        outcome={
            "plant_id": "PLANT-A",
            "tag": "PT-303",
            "actual_state": "DEGRADED",
        },
    )

    assert result["outcome_verification"]["status"] == "VERIFIED_MISMATCH"


def test_predictive_flow_rejects_cross_plant_outcome():
    try:
        run_predictive_flow(
            "PLANT-A",
            "PT-303",
            _observations(),
            predictor=_predictor,
            outcome={
                "plant_id": "PLANT-B",
                "tag": "PT-303",
                "actual_state": "NORMAL",
            },
        )
    except ValueError as exc:
        assert "cross-plant" in str(exc)
    else:
        raise AssertionError("cross-plant outcome was not rejected")


def test_predictive_flow_does_not_invoke_predictor_with_partial_evidence():
    calls = []

    def predictor(*, plant_id, tag, evidence):
        calls.append(True)
        return _predictor(plant_id=plant_id, tag=tag, evidence=evidence)

    observations = [
        {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0},
        {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "not-a-time", "value": 11.0},
        {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:02:00Z", "value": 12.0},
    ]

    result = run_predictive_flow(
        "PLANT-A", "PT-303", observations, predictor=predictor
    )

    assert result["evidence"]["quality"] == "PARTIAL"
    assert result["evidence"]["usable_observation_count"] == 2
    assert result["status"] == "NOT_INVOKED"
    assert calls == []
\n\ndef test_predictive_flow_blocks_when_evidence_falls_outside_requested_window():
    calls = []

    def predictor(*, plant_id, tag, evidence):
        calls.append(True)
        return _predictor(plant_id=plant_id, tag=tag, evidence=evidence)

    result = run_predictive_flow(
        "PLANT-A", "PT-303", _observations(), predictor=predictor,
        window_start="2026-09-20T10:00:00Z",
        window_end="2026-09-20T10:00:30Z",
    )

    assert result["evidence"]["window_status"] == "PARTIAL"
    assert result["status"] == "NOT_INVOKED"
    assert calls == []
