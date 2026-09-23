from v3.predictive_audit import build_predictive_execution_audit
from v3.predictive_flow import run_predictive_flow


def _observations():
    return [
        {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0},
        {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:01:00Z", "value": 10.2},
    ]


def _predictor(*, plant_id, tag, evidence):
    return {"plant_id": plant_id, "tag": tag, "predicted_state": "NORMAL"}


def test_alpha19_predictive_flow_exposes_provenance_audit():
    result = run_predictive_flow(
        "PLANT-A", "PT-303", _observations(), predictor=_predictor
    )
    audit = result["execution_audit"]

    assert audit["audit_type"] == "PREDICTIVE_EXECUTION_PROVENANCE"
    assert audit["plant_id"] == "PLANT-A"
    assert audit["tag"] == "PT-303"
    assert audit["evidence"]["quality"] == "VALID"
    assert audit["evidence"]["usable_observation_count"] == 2
    assert audit["context"]["context_status"] == "ASSEMBLED"
    assert audit["prediction"]["status"] == "INVOKED"
    assert audit["outcome_verification"]["status"] == "NOT_PROVIDED"
    assert audit["safety"]["read_only"] is True
    assert audit["safety"]["plc_write"] is False
    assert audit["safety"]["scada_control"] is False


def test_alpha19_audit_rejects_cross_plant_components():
    base = {
        "plant_id": "PLANT-A",
        "tag": "PT-303",
    }
    evidence = {**base, "quality": "VALID", "usable_observation_count": 2}
    context = {**base, "context_status": "ASSEMBLED"}
    prediction = {**base, "status": "INVOKED"}
    outcome = {**base, "status": "NOT_PROVIDED"}

    try:
        build_predictive_execution_audit(
            "PLANT-A",
            "PT-303",
            evidence=evidence,
            context={**context, "plant_id": "PLANT-B"},
            prediction=prediction,
            outcome_verification=outcome,
        )
    except ValueError as exc:
        assert "invalid plant scope" in str(exc)
    else:
        raise AssertionError("cross-plant audit component was accepted")


def test_alpha19_audit_is_not_an_execution_or_prediction_engine():
    result = run_predictive_flow(
        "PLANT-A", "PT-303", _observations(), predictor=_predictor
    )
    audit = result["execution_audit"]

    assert "probability" not in audit
    assert "rul" not in audit
    assert "diagnosis" not in audit
    assert "control_action" not in audit
