"""Regression tests for complete selected-plant critical-point reports."""
from anvi_critical_point_report import build_critical_point_report, is_critical_point_request


def test_critical_point_prompt_variants_route_to_report():
    prompts = [
        "Show all 25 critical points with tag, area and evidence.",
        "Reconcile the critical-point count and return every unique critical tag.",
        "List all critical tags from the selected plant without truncation.",
        "Show critical equipment.",
    ]
    assert all(is_critical_point_request(q) for q in prompts)


def test_unrelated_questions_do_not_match_critical_point_intent():
    assert not is_critical_point_request("Show the maintenance schedule.")
    assert not is_critical_point_request("What is current plant health?")


def test_report_returns_every_unique_tag_and_collapses_duplicates():
    points = [
        {
            "tag": f"TAG_{i:03d}", "area": "PCI", "description": f"Point {i}",
            "state": "CRITICAL", "value": i * 1.25, "timestamp": "2026-11-10T08:00:00Z",
            "source": "PCI DEMO STREAM",
        }
        for i in range(26)
    ]
    points.append(dict(points[0]))
    points[0]["metadata"] = {"unit": "degC", "high_high_limit": "120"}
    result = build_critical_point_report(
        {"mode": "SIMULATION", "source": "PCI DEMO STREAM", "points": points},
        plant_id="plant-a", plant_name="Test Plant",
    )
    assert result["count"] == 26
    assert result["source_row_count"] == 27
    assert result["duplicate_rows_collapsed"] == 1
    for i in range(26):
        assert f"TAG_{i:03d}" in result["answer"]
    assert "Unit: degC" in result["answer"]
    assert "Configured limit: 120" in result["answer"]
    assert "UNAVAILABLE" in result["answer"]
    assert "not live plant telemetry" in result["answer"]
    assert result["read_only"] is True
    assert result["plc_write"] is False
    assert result["scada_control"] is False
    assert result["automatic_authorization"] is False
    assert result["automatic_execution"] is False
    assert result["human_decision_required"] is True


def test_empty_selected_plant_returns_no_data_without_fallback():
    result = build_critical_point_report(
        {"status": "NO DATA", "mode": "ONBOARDING_DATA", "points": []},
        plant_id="plant-empty", plant_name="Empty Plant",
    )
    assert result["status"] == "NO_DATA"
    assert result["count"] == 0
    assert "no point records are onboarded in the selected plant snapshot" in result["answer"]
    assert "No other plant or global demo data was used." in result["answer"]
    assert result["plc_write"] is False
    assert result["scada_control"] is False
