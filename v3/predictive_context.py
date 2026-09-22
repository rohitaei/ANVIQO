"""Canonical tenant-scoped predictive context assembly.

Composition only: this module combines already validated V3 evidence, history,
and maintenance-memory results. It does not calculate predictions, trends,
probabilities, RUL, diagnosis, causation, or control actions.
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


def build_predictive_context(
    plant_id: str,
    tag: str,
    *,
    evidence: dict[str, Any],
    history: dict[str, Any] | None = None,
    maintenance_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plant_id = str(plant_id or "").strip()
    tag = str(tag or "").strip()
    if not plant_id or not tag:
        raise ValueError("plant_id and tag are required")

    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a dictionary")
    if str(evidence.get("plant_id") or "") != plant_id:
        raise ValueError("predictive evidence has invalid plant scope")
    if str(evidence.get("tag") or "") != tag:
        raise ValueError("predictive evidence tag mismatch")

    for name, value in (("history", history), ("maintenance_memory", maintenance_memory)):
        if value is None:
            continue
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a dictionary")
        if str(value.get("plant_id") or "") != plant_id:
            raise ValueError(f"{name} has invalid plant scope")
        if str(value.get("tag") or "") != tag:
            raise ValueError(f"{name} tag mismatch")

    return {
        "plant_id": plant_id,
        "tag": tag,
        "evidence": evidence,
        "history": history or {"status": "NOT_PROVIDED", "records": []},
        "maintenance_memory": maintenance_memory or {
            "status": "NOT_PROVIDED",
            "records": [],
        },
        "context_status": "ASSEMBLED",
        "safety": dict(SAFETY),
    }
