from v3.shift_report_qa import answer_shift_history_question, is_shift_history_question


def _rows(**kwargs):
    return [
        {
            "plant_id": kwargs["plant_id"],
            "organization_id": kwargs["organization_id"],
            "tag": kwargs["tag"],
            "value": 7.333333492,
            "timestamp": "2026-09-23T00:00:00+00:00",
            "source": "TATA METALIKS SHIFT MATERIAL REPORT",
            "provenance": "Tata Metaliks supplied report 2026-09-23",
        },
        {
            "plant_id": kwargs["plant_id"],
            "organization_id": kwargs["organization_id"],
            "tag": kwargs["tag"],
            "value": 6.837384224,
            "timestamp": "2026-09-23T01:00:00+00:00",
            "source": "TATA METALIKS SHIFT MATERIAL REPORT",
            "provenance": "Tata Metaliks supplied report 2026-09-23",
        },
    ]


def test_alpha32_detects_historical_hourly_question():
    assert is_shift_history_question("What were the hourly PT_303 values in the 23/09/2026 shift report?")


def test_alpha32_returns_exact_tenant_history_with_provenance():
    result = answer_shift_history_question(
        "What were the hourly PT_303 values in the 23/09/2026 shift report?",
        plant_id="plant-a",
        organization_id="org-a",
        history_provider=_rows,
    )
    assert result["status"] == "OK"
    assert result["tag"] == "PT-303"
    assert result["observation_count"] == 2
    assert result["observations"][0]["value"] == 7.333333492
    assert "Tata Metaliks supplied report 2026-09-23" in result["answer"]
    assert result["plc_write"] is False
    assert result["scada_control"] is False


def test_alpha32_blocks_cross_plant_history():
    def provider(**kwargs):
        return [{
            "plant_id": "plant-b",
            "organization_id": kwargs["organization_id"],
            "tag": kwargs["tag"],
            "value": 99.0,
            "timestamp": "2026-09-23T00:00:00+00:00",
        }]

    try:
        answer_shift_history_question(
            "What was the hourly PT_303 value in the historical shift report?",
            plant_id="plant-a",
            organization_id="org-a",
            history_provider=provider,
        )
    except ValueError as exc:
        assert "cross-plant" in str(exc)
    else:
        raise AssertionError("cross-plant historical evidence must be rejected")


def test_alpha32_does_not_create_a_prediction():
    result = answer_shift_history_question(
        "What were the hourly PT_303 values in the 23/09/2026 shift report?",
        plant_id="plant-a",
        organization_id="org-a",
        history_provider=_rows,
    )
    assert "prediction" not in result
    assert "trend" not in result["answer"].lower()
