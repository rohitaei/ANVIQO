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
            ("AT_202", "Mill inlet CO", 88.82, "ppm", "PIW 258"),
            ("LT_302", "Mill bed height", 55.0, "%", "PIW 262"),
            ("PT_303", "Mill outlet gas pressure", 68.0, "mmWC", "PIW 260"),
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


def test_simulation_source_never_overrides_selected_plant_pci_evidence():
    points = [
        {
            "tag": tag,
            "description": tag,
            "state": "HEALTHY",
            "value": 12.3,
            "timestamp": "2026-11-10T19:11:42Z",
            "source": "PCI UPDATED DRAWING.xlsx",
            "simulation_source": spare_source,
            "metadata": {"criticality": "HIGH"},
        }
        for tag, spare_source in [
            ("LT_302", "database/spares/critical_spares.xlsx#LT"),
            ("PT_303", "database/spares/critical_spares.xlsx#PT"),
        ]
    ]
    result = build_critical_point_report(
        {"mode": "SIMULATION", "source": "SELECTED_PLANT_HIGH_CRITICALITY_PCI_KNOWLEDGE",
         "critical_count": 2, "points": points},
        plant_id="primary-plant", plant_name="Primary Plant",
    )
    assert result["count"] == 2
    assert all(item["evidence"] == "PCI UPDATED DRAWING.xlsx" for item in result["evidence"])
    assert all(item["measurement_provenance"] == "SIMULATION SNAPSHOT (not live telemetry)" for item in result["evidence"])
    assert "Instrument evidence: PCI UPDATED DRAWING.xlsx" in result["answer"]
    assert "Measurement provenance: SIMULATION SNAPSHOT (not live telemetry)" in result["answer"]
    assert "critical_spares.xlsx" not in result["answer"]
    assert "Unit: UNAVAILABLE" in result["answer"]
    assert "Configured limit: UNAVAILABLE" in result["answer"]
    assert result["plc_write"] is False
    assert result["scada_control"] is False



def test_documented_interlock_reference_is_not_mislabelled_as_live_configured_limit():
    point = {
        "tag": "AT_201",
        "name": "Mill inlet O2",
        "area": "VRM / MILL",
        "state": "HEALTHY",
        "value": 60.28,
        "timestamp": "2026-11-10T20:12:07Z",
        "source": "PCI UPDATED DRAWING.xlsx",
        "mode": "SIMULATION",
        "metadata": {
            "criticality": "HIGH",
            "engineering_unit": "%",
            "engineering_unit_source": "TMLPCI-ANDE-15-AUT-DE-D0055-01-0.pdf, page 5",
            "documented_interlock_reference": "AT_201_O2_LVL_VRM_IL: oxygen at VRM inlet >12% (start and run interlock)",
            "documented_interlock_source": "TMLPCI-ANDE-15-AUT-DE-D0055-01-0.pdf, page 5",
            "configuration_status": "DOCUMENT_REFERENCE_ONLY; current PLC/HMI setting not verified",
        },
    }
    result = build_critical_point_report(
        {"mode": "SIMULATION", "source": "SELECTED_PLANT_HIGH_CRITICALITY_PCI_KNOWLEDGE",
         "critical_count": 1, "points": [point]},
        plant_id="primary-plant", plant_name="Primary Plant",
    )
    assert "Unit: %" in result["answer"]
    assert "Configured limit: UNAVAILABLE" in result["answer"]
    assert "Documented interlock reference (not proof of current PLC/HMI setting): AT_201_O2_LVL_VRM_IL: oxygen at VRM inlet >12%" in result["answer"]
    assert "TMLPCI-ANDE-15-AUT-DE-D0055-01-0.pdf, page 5" in result["answer"]
    assert "Simulation scaling: UNVERIFIED" in result["answer"]
    assert "simulated values must not be compared with documented engineering limits" in result["answer"]
    assert result["evidence"][0]["configured_limit"] == "UNAVAILABLE"
    assert result["evidence"][0]["documented_interlock_reference"].startswith("AT_201_O2_LVL_VRM_IL")
    assert result["evidence"][0]["simulation_scale_status"].startswith("UNVERIFIED")
    assert result["plc_write"] is False
    assert result["scada_control"] is False
