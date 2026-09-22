"""V3 tenant-safe bridge to existing predictive intelligence.

This module is an orchestration boundary only. It never implements prediction,
trend, probability, RUL, diagnosis, thresholds, or control logic.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Dict

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


def invoke_existing_predictor(
    request: Dict[str, Any],
    predictor: Callable[..., Any] | None = None,
) -> Dict[str, Any]:
    """Invoke an existing predictor only when it explicitly accepts tenant scope.

    A legacy/global predictor is deliberately NOT invoked. This prevents V3
    from silently reading another plant's data through a global data source.
    """
    if not isinstance(request, dict):
        raise TypeError("request must be a dict")

    plant_id = str(request.get("plant_id") or "").strip()
    tag = str(request.get("tag") or "").strip()
    if not plant_id or not tag:
        raise ValueError("plant_id and tag are required")

    evidence = request.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("request evidence must be a list")

    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("each evidence item must be a dict")
        item_plant = item.get("plant_id")
        if item_plant is not None and str(item_plant) != plant_id:
            raise ValueError("cross-plant predictive evidence rejected")

    if request.get("status") != "READY_FOR_EXISTING_PREDICTOR":
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "Predictive evidence gate is not ready.",
            "safety": dict(SAFETY),
        }

    if predictor is None:
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "No existing tenant-aware predictor was supplied.",
            "safety": dict(SAFETY),
        }

    try:
        signature = inspect.signature(predictor)
    except (TypeError, ValueError):
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "Predictor signature could not be verified as tenant-aware.",
            "safety": dict(SAFETY),
        }

    parameters = signature.parameters
    if "plant_id" not in parameters:
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "Existing predictor does not declare plant_id; legacy/global predictors are blocked.",
            "safety": dict(SAFETY),
        }

    result = predictor(plant_id=plant_id, tag=tag, evidence=evidence)
    return {
        "plant_id": plant_id,
        "tag": tag,
        "status": "INVOKED",
        "result": result,
        "safety": dict(SAFETY),
    }
