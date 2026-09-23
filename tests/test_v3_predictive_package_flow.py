from v3.predictive_package_flow import run_predictive_flow_from_package


def _package(plant_id="PLANT-A"):
    return {
        "plant": {"plant_id": plant_id},
        "records": [{
            "tag": "PT-303",
            "external_id": "PT-303",
            "metadata": {
                "predictive_history": [
                    {"plant_id": plant_id, "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0},
                    {"plant_id": plant_id, "tag": "PT-303", "timestamp": "2026-09-20T11:00:00Z", "value": 12.0},
                ],
                "events": [],
                "maintenance_memory": [],
                "equipment_health": {"plant_id": plant_id, "tag": "PT-303", "status": "WATCH"},
            },
        }],
    }


def _observations():
    return [
        {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0},
        {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T11:00:00Z", "value": 12.0},
    ]


def test_alpha14_uses_real_package_sources_and_existing_predictor():
    result = run_predictive_flow_from_package(
        "PLANT-A", "PT-303", _observations(), package=_package()
    )
    prediction = result["prediction"]["result"]
    assert result["status"] == "INVOKED"
    assert prediction["plant_id"] == "PLANT-A"
    assert prediction["tag"] == "PT-303"
    assert prediction["status"] == "PREDICTION_AVAILABLE"
    assert prediction["trend"]["direction"] == "RISING"
    assert prediction["evidence_summary"]["persisted_observation_count"] == 2
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False


def test_alpha14_rejects_package_from_other_plant():
    try:
        run_predictive_flow_from_package(
            "PLANT-A", "PT-303", _observations(), package=_package("PLANT-B")
        )
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("cross-plant package was accepted")


def test_alpha14_requires_explicit_package_plant_identity():
    package = _package()
    package["records"][0]["metadata"]["predictive_history"][0].pop("plant_id")
    try:
        run_predictive_flow_from_package(
            "PLANT-A", "PT-303", _observations(), package=package
        )
    except ValueError as exc:
        assert "must carry plant_id" in str(exc)
    else:
        raise AssertionError("evidence without plant_id was accepted")
