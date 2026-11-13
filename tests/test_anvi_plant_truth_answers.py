from anvi_plant_truth_answers import recognizes_plant_truth_question, answer_plant_truth


def _assurance():
    return {
        "assurance_status": "CONSISTENT_SIMULATION_EVIDENCE",
        "recomputed_health_score": 75.0,
        "state_counts": {"HEALTHY": 2, "WARNING": 1, "CRITICAL": 1},
        "checks": {
            "point_total_reconciled": True,
            "state_counts_reconciled": True,
            "health_score_reconciled": True,
            "timestamp_valid": True,
            "snapshot_fresh": True,
        },
        "findings": ["SIMULATION_NOT_LIVE_TELEMETRY"],
    }


def _snapshot():
    return {
        "plant_id": "p-1",
        "mode": "SIMULATION",
        "source": "PCI DEMO STREAM",
        "points": [
            {"tag": "PT-1", "state": "HEALTHY"},
            {"tag": "PT-2", "state": "HEALTHY", "changed": True},
            {"tag": "PT-3", "state": "WARNING", "event_active": True},
            {"tag": "PT-4", "state": "CRITICAL", "event_active": True},
        ],
    }


def test_plant_health_answer_uses_reconciled_assurance_score():
    result = answer_plant_truth("What is the current plant health?", _snapshot(), _assurance())
    assert result["plant_health_score"] == 75.0
    assert "SIMULATION ONLY" in result["answer"]
    assert result["counts"]["CRITICAL"] == 1
    assert result["plc_write"] is False


def test_inconsistent_health_evidence_does_not_publish_a_score():
    assurance = _assurance()
    assurance["checks"]["active_event_count_reconciled"] = False
    assurance["assurance_status"] = "PARTIAL_OR_INCONSISTENT_EVIDENCE"
    assurance["recomputed_health_score"] = None
    result = answer_plant_truth("Plant health", _snapshot(), assurance)
    assert result["plant_health_score"] is None
    assert "cannot provide one definitive" in result["answer"]


def test_alarm_and_critical_lists_are_point_level_and_consistent():
    alarms = answer_plant_truth("Show active alarms", _snapshot(), _assurance())
    critical = answer_plant_truth("Show critical equipment", _snapshot(), _assurance())
    assert alarms["matched_count"] == 2
    assert critical["matched_count"] == 1
    assert "PT-4" in critical["answer"]


def test_non_plant_truth_question_is_not_intercepted():
    assert recognizes_plant_truth_question("Explain a 4-20 mA transmitter") is False
    assert answer_plant_truth("Explain a 4-20 mA transmitter", _snapshot(), _assurance()) is None


def test_simulation_reseeding_is_explicit_in_runtime_adapter():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "anvi_universal_command_centre.py").read_text(encoding="utf-8")
    assert "simulator.reset_simulation_window()" in source
