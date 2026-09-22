"""V3 canonical tenant-safe prediction result contract.

This module validates the boundary output of an existing predictor. It does not
interpret the result, calculate probability/RUL/trend, diagnose causes, or
perform control actions.
"""
from __future__ import annotations

from typing import Any

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


def validate_prediction_result(
    plant_id: str,
    tag: str,
    result: Any,
) -> dict[str, Any]:
    """Validate an existing predictor result for exact tenant/tag scope."""
    plant_id = str(plant_id or "").strip()
    tag = str(tag or "").strip()
    if not plant_id or not tag:
        raise ValueError("plant_id and tag are required")
    if not isinstance(result, dict):
        raise ValueError("existing predictor must return a dictionary")

    result_plant = str(result.get("plant_id") or "").strip()
    result_tag = str(result.get("tag") or "").strip()
    if result_plant != plant_id:
        raise ValueError("prediction result has invalid plant scope")
    if result_tag != tag:
        raise ValueError("prediction result tag mismatch")

    return {
        "plant_id": plant_id,
        "tag": tag,
        "status": "VALIDATED",
        "result": result,
        "safety": dict(SAFETY),
    }
