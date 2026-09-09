import failure_prediction_demo_api as demo


def test_demo_prediction_is_explicitly_simulation_only():
    result = demo.build_demo_failure_prediction("PT-303")
    assert result["status"] == "DEMO_PREDICTION_AVAILABLE"
    assert result["simulation"] is True
    assert result["source"] == "SIMULATION"
    assert result["observations"] == 8
    assert result["first_value"] == 48.2
    assert result["last_value"] == 53.7
    assert result["delta"] == 5.5
    assert result["direction"] == "RISING"
    assert result["failure_probability"] is None
    assert result["failure_date"] is None
    assert result["production_history_write"] is False
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False
    assert result["decision_status"] == "HUMAN_DECISION_REQUIRED"


def test_demo_query_detector_requires_demo_and_prediction_intent():
    assert demo.is_demo_failure_prediction_query("Predict PT-303 using demo data")
    assert demo.is_demo_failure_prediction_query("Show synthetic failure trend")
    assert not demo.is_demo_failure_prediction_query("Predict PT-303")
    assert not demo.is_demo_failure_prediction_query("Show PT-303 demo")
