from v3.predictive_maintenance import (
    PredictionEvidence,
    build_prediction_request,
    run_existing_predictor,
)


def test_prediction_evidence_is_tenant_scoped():
    evidence = PredictionEvidence(
        "PLANT-A",
        "PT-303",
        ({"plant_id": "PLANT-A", "timestamp": "2026-09-22T10:00:00Z", "value": 10},),
    )
    assert evidence.numeric_timestamped_count == 1


def test_cross_plant_evidence_is_rejected():
    try:
        PredictionEvidence(
            "PLANT-A",
            "PT-303",
            ({"plant_id": "PLANT-B", "timestamp": "2026-09-22T10:00:00Z", "value": 10},),
        )
    except ValueError:
        return
    assert False, "cross-plant evidence must be rejected"


def test_insufficient_evidence_does_not_invoke_predictor():
    request = build_prediction_request(
        "PLANT-A",
        "PT-303",
        [{"timestamp": "2026-09-22T10:00:00Z", "value": 10}],
    )
    called = []
    result = run_existing_predictor(
        request,
        lambda **kwargs: called.append(kwargs) or {"prediction": "unexpected"},
    )
    assert result["status"] == "NOT_INVOKED"
    assert called == []
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False


def test_ready_request_calls_only_supplied_predictor():
    request = build_prediction_request(
        "PLANT-A",
        "PT-303",
        [
            {"plant_id": "PLANT-A", "timestamp": "2026-09-22T10:00:00Z", "value": 10},
            {"plant_id": "PLANT-A", "timestamp": "2026-09-22T11:00:00Z", "value": 12},
        ],
    )

    def predictor(*, plant_id, tag, evidence):
        return {
            "plant_id": plant_id,
            "tag": tag,
            "predicted_state": "NORMAL",
            "observations": len(evidence),
        }

    result = run_existing_predictor(request, predictor)
    assert request["status"] == "READY_FOR_EXISTING_PREDICTOR"
    assert result["status"] == "INVOKED"
    assert result["result"]["plant_id"] == "PLANT-A"
    assert result["result"]["tag"] == "PT-303"
    assert result["safety"]["human_decision_required"] is True
