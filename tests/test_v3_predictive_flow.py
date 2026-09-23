from v3.predictive_flow import run_predictive_flow


def test_predictive_flow_invokes_only_tenant_aware_predictor():
    calls = []

    def predictor(*, plant_id, tag, evidence):
        calls.append((plant_id, tag, len(evidence)))
        return {
            "plant_id": plant_id,
            "tag": tag,
            "predicted_state": "NORMAL",
        }

    result = run_predictive_flow(
        "PLANT-A",
        "PT-303",
        [
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0},
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:01:00Z", "value": 10.2},
        ],
        predictor=predictor,
    )

    assert result["status"] == "INVOKED"
    assert result["prediction"]["result"]["plant_id"] == "PLANT-A"
    assert calls == [("PLANT-A", "PT-303", 2)]
    assert result["safety"]["read_only"] is True
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False


def test_predictive_flow_does_not_invoke_predictor_with_insufficient_evidence():
    calls = []

    def predictor(*, plant_id, tag, evidence):
        calls.append(True)
        return {
            "plant_id": plant_id,
            "tag": tag,
            "predicted_state": "NORMAL",
        }

    result = run_predictive_flow(
        "PLANT-A",
        "PT-303",
        [{"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0}],
        predictor=predictor,
    )

    assert result["status"] == "NOT_INVOKED"
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
        "PLANT-A",
        "PT-303",
        [
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0},
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:01:00Z", "value": 10.2},
        ],
        predictor=legacy_predictor,
    )

    assert result["status"] == "NOT_INVOKED"
    assert "legacy/global" in result["prediction"]["reason"]
