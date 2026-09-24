"""V3 predictive execution provenance contract.

This module records the deterministic boundary state of one predictive flow.
It does not persist data, calculate predictions, interpret results, or perform
control actions. Persistence remains the responsibility of the caller.
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


def build_predictive_execution_audit(
    plant_id: str,
    tag: str,
    *,
    evidence: dict[str, Any],
    context: dict[str, Any],
    prediction: dict[str, Any],
    outcome_verification: dict[str, Any],
) -> dict[str, Any]:
    """Build a tenant-scoped, deterministic audit record for one flow."""
    plant_id = str(plant_id or "").strip()
    tag = str(tag or "").strip()
    if not plant_id or not tag:
        raise ValueError("plant_id and tag are required")

    for name, value in (
        ("evidence", evidence),
        ("context", context),
        ("prediction", prediction),
        ("outcome_verification", outcome_verification),
    ):
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a dictionary")
        if str(value.get("plant_id") or "").strip() != plant_id:
            raise ValueError(f"{name} has invalid plant scope")
        if str(value.get("tag") or "").strip() != tag:
            raise ValueError(f"{name} tag mismatch")

    return {
        "plant_id": plant_id,
        "tag": tag,
        "audit_type": "PREDICTIVE_EXECUTION_PROVENANCE",
        "evidence": {
            "quality": evidence.get("quality"),
            "usable_observation_count": evidence.get("usable_observation_count"),
            "invalid_observation_count": evidence.get("invalid_observation_count"),
            "timestamp_start": evidence.get("timestamp_start"),
            "timestamp_end": evidence.get("timestamp_end"),
            "span_seconds": evidence.get("span_seconds"),
            "window_start": evidence.get("window_start"),
            "window_end": evidence.get("window_end"),
            "window_status": evidence.get("window_status"),
        },
        "context": {
            "context_status": context.get("context_status"),
            "history_status": (context.get("history") or {}).get("status"),
            "maintenance_memory_status": (
                (context.get("maintenance_memory") or {}).get("status")
            ),
        },
        "prediction": {
            "status": prediction.get("status"),
            "reason": prediction.get("reason"),
        },
        "outcome_verification": {
            "status": outcome_verification.get("status"),
        },
        "safety": dict(SAFETY),
    }
