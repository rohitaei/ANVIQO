from v3.predictive_context import build_predictive_context


def _evidence():
    return {"plant_id": "PLANT-A", "tag": "PT-303", "status": "READY"}


def test_context_assembles_same_tenant_inputs():
    result = build_predictive_context(
        "PLANT-A",
        "PT-303",
        evidence=_evidence(),
        history={"plant_id": "PLANT-A", "tag": "PT-303", "records": []},
        maintenance_memory={
            "plant_id": "PLANT-A",
            "tag": "PT-303",
            "records": [],
        },
    )
    assert result["context_status"] == "ASSEMBLED"
    assert result["safety"]["plc_write"] is False


def test_cross_plant_evidence_is_rejected():
    try:
        build_predictive_context(
            "PLANT-A",
            "PT-303",
            evidence={"plant_id": "PLANT-B", "tag": "PT-303"},
        )
    except ValueError as exc:
        assert "evidence" in str(exc)
    else:
        raise AssertionError("cross-plant evidence must be rejected")


def test_cross_plant_history_is_rejected():
    try:
        build_predictive_context(
            "PLANT-A",
            "PT-303",
            evidence=_evidence(),
            history={"plant_id": "PLANT-B", "tag": "PT-303", "records": []},
        )
    except ValueError as exc:
        assert "history" in str(exc)
    else:
        raise AssertionError("cross-plant history must be rejected")


def test_cross_plant_memory_is_rejected():
    try:
        build_predictive_context(
            "PLANT-A",
            "PT-303",
            evidence=_evidence(),
            maintenance_memory={
                "plant_id": "PLANT-B",
                "tag": "PT-303",
                "records": [],
            },
        )
    except ValueError as exc:
        assert "maintenance_memory" in str(exc)
    else:
        raise AssertionError("cross-plant maintenance memory must be rejected")


def test_tag_mismatch_is_rejected():
    try:
        build_predictive_context(
            "PLANT-A",
            "PT-303",
            evidence={"plant_id": "PLANT-A", "tag": "FT-404"},
        )
    except ValueError as exc:
        assert "tag mismatch" in str(exc)
    else:
        raise AssertionError("tag mismatch must be rejected")
