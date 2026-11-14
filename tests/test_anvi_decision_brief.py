from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("anvi_decision_brief", ROOT / "anvi_decision_brief.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_tag_brief_preserves_source_and_safety():
    result = _load().build_equipment_brief({
        "mode": "SIMULATION",
        "points": [{
            "tag": "PT_303", "name": "Mill outlet gas pressure",
            "area": "VRM/MILL", "io_type": "AI", "plc_address": "PIW 260",
            "value": 68.0, "state": "WARNING", "changed": True,
            "event_active": True, "timestamp": "2026-11-14T00:00:00+00:00",
            "source": "PCI DEMO STREAM",
        }],
    }, "PT-303")
    assert result["status"] == "BRIEF_READY"
    assert result["equipment"]["tag"] == "PT_303"
    assert result["decision_priority"] == "P2_ENGINEERING_REVIEW"
    assert result["evidence_quality"] == "SIMULATION_ONLY_NOT_LIVE_TELEMETRY"
    assert any("Synthetic demo values are not measured plant telemetry" in item for item in result["limitations"])
    assert result["plc_write"] is False and result["scada_control"] is False
    assert result["automatic_execution"] is False


def test_exact_tag_lookup_never_falls_back_to_another_equipment():
    result = _load().build_equipment_brief({
        "mode": "SIMULATION", "points": [{"tag": "PT-303", "state": "HEALTHY"}],
    }, "PT-304")
    assert result["status"] == "EQUIPMENT_NOT_FOUND"
    assert result["match_count"] == 0


def test_duplicate_normalized_tags_are_rejected_as_ambiguous():
    result = _load().build_equipment_brief({
        "mode": "SIMULATION",
        "points": [{"tag": "PT-303"}, {"tag": "PT_303"}],
    }, "PT-303")
    assert result["status"] == "AMBIGUOUS_EQUIPMENT_IDENTITY"


def test_onboarding_points_are_not_presented_as_live_telemetry():
    result = _load().build_equipment_brief({
        "mode": "ONBOARDING_DATA",
        "points": [{"tag": "PT-304", "state": "ONBOARDED_DATA"}],
    }, "PT-304")
    assert result["evidence_quality"] == "ONBOARDING_DATA_NOT_LIVE_TELEMETRY"



def test_same_tag_spare_inventory_row_does_not_make_instrument_identity_ambiguous():
    result = _load().build_equipment_brief({
        "mode": "SIMULATION",
        "points": [
            {"tag": "PT_303", "record_type": "INSTRUMENT", "name": "Mill outlet gas pressure", "state": "CRITICAL", "value": 34.15},
            {"tag": "PT-303", "record_type": "CRITICAL_SPARE", "asset_type": "CRITICAL_SPARE", "name": "PT spare", "state": "WARNING", "value": 9},
        ],
    }, "PT-303")
    assert result["status"] == "BRIEF_READY"
    assert result["equipment"]["tag"] == "PT_303"
    assert result["equipment"]["state"] == "CRITICAL"
    assert result["excluded_inventory_match_count"] == 1
    assert "1 inventory-only record(s) excluded" in result["identity_resolution"]


def test_two_operational_records_with_same_normalized_tag_remain_ambiguous():
    result = _load().build_equipment_brief({
        "mode": "SIMULATION",
        "points": [
            {"tag": "PT-303", "record_type": "INSTRUMENT"},
            {"tag": "PT_303", "record_type": "INSTRUMENT"},
            {"tag": "PT-303", "record_type": "CRITICAL_SPARE"},
        ],
    }, "PT-303")
    assert result["status"] == "AMBIGUOUS_EQUIPMENT_IDENTITY"
    assert result["match_count"] == 2
    assert result["excluded_inventory_match_count"] == 1



def test_unassessed_equipment_brief_does_not_claim_routine_healthy_state():
    result = _load().build_equipment_brief({
        "mode": "SIMULATION",
        "points": [{
            "tag": "PT_303",
            "name": "Mill outlet gas pressure",
            "state": "UNASSESSED",
            "value": 12.24,
            "value_basis": "SYNTHETIC_DEMO_VALUE_NOT_ENGINEERING_MEASUREMENT",
            "source": "PCI DEMO STREAM",
        }],
    }, "PT-303")
    assert result["status"] == "BRIEF_READY"
    assert result["decision_priority"] == "EVIDENCE_REVIEW"
    assert result["what_matters"] == "Validate the observation before drawing a conclusion"
    assert result["evidence_quality"] == "SIMULATION_ONLY_NOT_LIVE_TELEMETRY"
    assert result["equipment"]["value_basis"] == "SYNTHETIC_DEMO_VALUE_NOT_ENGINEERING_MEASUREMENT"
