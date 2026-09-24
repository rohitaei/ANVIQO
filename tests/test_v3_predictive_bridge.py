from v3.predictive_maintenance import build_prediction_request
from v3.predictive_bridge import invoke_existing_predictor


def _request():
    return build_prediction_request(
        "PLANT-A",
        "PT-303",
        [
            {"plant_id": "PLANT-A", "timestamp": "2026-09-20T10:00:00Z", "value": 10},
            {"plant_id": "PLANT-A", "timestamp": "2026-09-20T10:01:00Z", "value": 11},
        ],
    )


def test_legacy_global_predictor_is_blocked():
    def legacy(tag, evidence):
        return {"bad": True}

    result = invoke_existing_predictor(_request(), legacy)
    assert result["status"] == "NOT_INVOKED"
    assert "tenant-aware" in result["reason"] or "legacy/global" in result["reason"]


def test_tenant_aware_predictor_is_invoked():
    seen = {}

    def predictor(*, plant_id, tag, evidence):
        seen.update(plant_id=plant_id, tag=tag, evidence=evidence)
        return {"plant_id": plant_id, "tag": tag, "predicted_state": "NORMAL"}

    result = invoke_existing_predictor(_request(), predictor)
    assert result["status"] == "INVOKED"
    assert seen["plant_id"] == "PLANT-A"
    assert seen["tag"] == "PT-303"


def test_cross_plant_evidence_is_rejected():
    request = _request()
    request["evidence"][1]["plant_id"] = "PLANT-B"
    try:
        invoke_existing_predictor(request, lambda **kwargs: None)
    except ValueError as exc:
        assert "cross-plant" in str(exc)
    else:
        raise AssertionError("cross-plant evidence must be rejected")


def test_safety_contract():
    result = invoke_existing_predictor(_request())
    assert result["safety"] == {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "automatic_action": False,
        "human_decision_required": True,
    }
