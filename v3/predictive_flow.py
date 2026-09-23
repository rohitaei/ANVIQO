"""Canonical V3 predictive maintenance orchestration boundary.

This module composes existing V3 contracts into one tenant-safe, read-only
execution path. It does not implement prediction, trend analysis, RUL,
diagnosis, causation, thresholds, or control actions.
"""
from __future__ import annotations

from typing import Any, Callable

from v3.predictive_bridge import invoke_existing_predictor
from v3.predictive_context import build_predictive_context
from v3.predictive_evidence import validate_prediction_evidence
from v3.predictive_history_bridge import fetch_tenant_predictive_history
from v3.maintenance_memory_bridge import fetch_tenant_maintenance_memory

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


def run_predictive_flow(
    plant_id: str,
    tag: str,
    observations: list[dict[str, Any]],
    *,
    predictor: Callable[..., Any] | None = None,
    history_provider: Callable[..., Any] | None = None,
    maintenance_memory_provider: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run the canonical V3 predictive boundary without adding intelligence.

    The flow is strictly:
    evidence validation -> optional tenant-scoped history/memory -> context
    assembly -> existing tenant-aware predictor -> validated result.

    A predictor is never invoked unless the canonical evidence gate is ready.
    """
    plant_id = str(plant_id or "").strip()
    tag = str(tag or "").strip()
    if not plant_id or not tag:
        raise ValueError("plant_id and tag are required")
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")

    evidence = validate_prediction_evidence(plant_id, tag, observations)
    history = fetch_tenant_predictive_history(
        plant_id, tag, provider=history_provider
    )
    maintenance_memory = fetch_tenant_maintenance_memory(
        plant_id, tag, provider=maintenance_memory_provider
    )

    context = build_predictive_context(
        plant_id,
        tag,
        evidence=evidence,
        history=history,
        maintenance_memory=maintenance_memory,
    )

    request = {
        "plant_id": plant_id,
        "tag": tag,
        "status": (
            "READY_FOR_EXISTING_PREDICTOR"
            if evidence["quality"] == "VALID"
            else "INSUFFICIENT_EVIDENCE"
        ),
        "evidence": evidence["evidence"],
        "context": context,
    }
    prediction = invoke_existing_predictor(request, predictor=predictor)

    return {
        "plant_id": plant_id,
        "tag": tag,
        "status": prediction["status"],
        "evidence": evidence,
        "context": context,
        "prediction": prediction,
        "safety": dict(SAFETY),
    }
