from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("anvi_decision_brief", ROOT / "anvi_decision_brief.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_tag_decision_brief_is_evidence_first_and_safe():
    result = _load().build_equipment_brief({
        "mode": "SIMULATION",
        "points": [{
            "tag": "PT_303", "description": "Mill outlet gas pressure",
            "area": "VRM/MILL", "io_type": "AI", "plc_address": "PIW 260",
            "value": 68.0, "state": "WARNING", "changed": True,
            "event_active": True, "timestamp": "2026-11-14T00:00:00+00:00",
            "mode": "SIMULATION", "source": "PCI DEMO STREAM",
        }],
    }, "PT-303")
    assert result["status"] == "BRIEF_READY"
    assert result["decision_priority"] == "P2_ENGINEERING_REVIEW"
    assert result["evidence_quality"] == "SIMULATION_ONLY_NOT_LIVE_TELEMETRY"
    assert result["plc_write"] is False and result["scada_control"] is False
    assert result["automatic_execution"] is False


def test_decision_brief_never_fuzzy_matches_an_unknown_tag():
    result = _load().build_equipment_brief({
        "mode": "SIMULATION", "points": [{"tag": "PT-303", "state": "HEALTHY"}],
    }, "PT-304")
    assert result["status"] == "EQUIPMENT_NOT_FOUND"
    assert result["match_count"] == 0


def test_ambiguous_normalized_tag_is_rejected():
    result = _load().build_equipment_brief({
        "mode": "SIMULATION",
        "points": [{"tag": "PT-303", "state": "HEALTHY"}, {"tag": "PT_303", "state": "HEALTHY"}],
    }, "PT-303")
    assert result["status"] == "AMBIGUOUS_EQUIPMENT_IDENTITY"
