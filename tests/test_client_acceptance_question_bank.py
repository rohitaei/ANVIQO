"""Structural checks for the ANVIQO client acceptance corpus.

These tests validate coverage and safety expectations in the dataset. They do not
claim that the live chatbot has answered the prompts; runtime execution is a
separate authenticated staging acceptance step.
"""
import json
from pathlib import Path

BANK = Path(__file__).resolve().parents[1] / "tests" / "data" / "anviqo_client_acceptance_questions.json"
REQUIRED_CATEGORIES = {
    "plant_health", "alarms_events", "pci_identity", "instrumentation_troubleshooting",
    "predictive_reliability", "maintenance_reports", "critical_spares", "operations_process",
    "automation_electrical", "mechanical_utilities", "safety_compliance", "enterprise_scope",
    "robustness_adversarial",
}


def load_bank():
    return json.loads(BANK.read_text(encoding="utf-8"))


def test_bank_has_195_unique_questions_and_expected_categories():
    bank = load_bank()
    questions = bank["questions"]
    assert bank["question_count"] == len(questions) == 195
    assert len({item["id"] for item in questions}) == 195
    assert len({item["question"] for item in questions}) == 195
    assert {item["category"] for item in questions} == REQUIRED_CATEGORIES


def test_every_question_has_an_expected_response_contract():
    for item in load_bank()["questions"]:
        assert item["question"].strip()
        assert item["expected_intent"]
        assert item["expected_behavior"]
        assert item["required_evidence"]


def test_every_question_preserves_read_only_human_governed_safety():
    for item in load_bank()["questions"]:
        safety = item["safety_contract"]
        assert safety == {
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "automatic_authorization": False,
            "automatic_execution": False,
            "human_decision_required": True,
        }


def test_unsafe_prompts_are_explicitly_included():
    prompts = [item["question"].lower() for item in load_bank()["questions"]]
    assert any("force this output" in q for q in prompts)
    assert any("bypass" in q for q in prompts)
    assert any("authorize a permit" in q for q in prompts)


def test_cross_plant_and_missing_evidence_cases_are_explicitly_included():
    prompts = [item["question"].lower() for item in load_bank()["questions"]]
    assert any("another plant" in q for q in prompts)
    assert any("make a reasonable guess" in q for q in prompts)
    assert any("no source" in q for q in prompts)
}
