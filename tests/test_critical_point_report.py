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
        {"mode": "SIMULATION", "source": "PCI DEMO STREAM", "critical": 27, "points": points},
        plant_id="plant-a", plant_name="Test Plant",
    )
    assert result["count"] == 26
    assert result["source_row_count"] == 27
    assert result["duplicate_rows_collapsed"] == 1
    assert result["snapshot_reported_critical_count"] == "27"
    assert result["count_reconciliation"] == "MATCH"
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


def test_report_includes_all_onboarded_high_criticality_tags_even_without_alarm_state():
    points = [
        {
            "tag": tag,
            "name": name,
            "area": "VRM / MILL",
            "state": "HEALTHY",
            "value": value,
            "timestamp": "2026-11-10T10:00:00Z",
            "source": "PCI DEMO STREAM",
            "metadata": {"criticality": "HIGH", "unit": unit, "plc_address": address},
        }
        for tag, name, value, unit, address in [
            ("AT_201", "Mill inlet O2", 8.2, "%", "PIW 256"),
            ("AT_202", "Mill inlet CO", 0.04, "%", "PIW 258"),
            ("LT_302", "Mill bed height", 55.0, "%", "PIW 262"),
            ("PT_303", "Mill outlet gas pressure", 68.0, "mbar", "PIW 260"),
        ]
    ]
    result = build_critical_point_report(
        {"mode": "SIMULATION", "source": "SELECTED_PLANT_HIGH_CRITICALITY_PCI_KNOWLEDGE",
         "critical_count": 4, "points": points},
        plant_id="primary-plant", plant_name="Primary Plant",
    )
    assert result["count"] == 4
    assert result["count_reconciliation"] == "MATCH"
    assert all(tag in result["answer"] for tag in ("AT_201", "AT_202", "LT_302", "PT_303"))
    assert all(item["severity"] == "HIGH CRITICALITY" for item in result["evidence"])
    assert "asset classification, not proof of an active alarm" in result["answer"]
    assert "Configured limit: UNAVAILABLE" in result["answer"]
    assert result["plc_write"] is False
    assert result["scada_control"] is False
