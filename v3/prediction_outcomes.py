"""V3 prediction outcome verification contract.

This module evaluates only explicitly supplied prediction/outcome evidence.
It does not generate predictions, infer outcomes, train models, or control
plant equipment.
"""
from __future__ import annotations

from typing import Any, Dict

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


def verify_prediction_outcome(
    prediction: Dict[str, Any],
    outcome: Dict[str, Any],
) -> Dict[str, Any]:
    """Verify an explicitly supplied prediction against an explicit outcome.

    No prediction or outcome is inferred. The two records must carry the same
    tenant and tag, and both must provide explicit comparable states.
    """
    if not isinstance(prediction, dict) or not isinstance(outcome, dict):
        raise TypeError("prediction and outcome must be dicts")

    plant_id = str(prediction.get("plant_id") or "").strip()
    tag = str(prediction.get("tag") or "").strip()
    outcome_plant = str(outcome.get("plant_id") or "").strip()
    outcome_tag = str(outcome.get("tag") or "").strip()

    if not plant_id or not tag or not outcome_plant or not outcome_tag:
        raise ValueError("plant_id and tag are required on prediction and outcome")
    if outcome_plant != plant_id:
        raise ValueError("cross-plant prediction outcome rejected")
    if outcome_tag != tag:
        raise ValueError("prediction/outcome tag mismatch")

    predicted_state = prediction.get("predicted_state")
    actual_state = outcome.get("actual_state")
    if predicted_state is None or actual_state is None:
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "UNVERIFIED",
            "reason": "Explicit predicted_state and actual_state are required; no outcome is inferred.",
            "safety": dict(SAFETY),
        }

    matched = predicted_state == actual_state
    return {
        "plant_id": plant_id,
        "tag": tag,
        "status": "VERIFIED_MATCH" if matched else "VERIFIED_MISMATCH",
        "predicted_state": predicted_state,
        "actual_state": actual_state,
        "safety": dict(SAFETY),
    }
