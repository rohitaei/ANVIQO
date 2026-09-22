"""V3 tenant-safe predictive history provider bridge.

This module accepts historical observations only from an explicitly
tenant-scoped provider. It does not read legacy/global history stores,
calculate trends, or perform prediction.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


def fetch_tenant_predictive_history(
    plant_id: str,
    tag: str,
    provider: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Fetch predictive history only from a provider that declares plant scope."""
    plant_id = str(plant_id or "").strip()
    tag = str(tag or "").strip()
    if not plant_id or not tag:
        raise ValueError("plant_id and tag are required")

    if provider is None:
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "No existing tenant-scoped predictive history provider was supplied.",
            "observations": [],
            "safety": dict(SAFETY),
        }

    try:
        parameters = inspect.signature(provider).parameters
    except (TypeError, ValueError):
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "History provider signature could not be verified as tenant-aware.",
            "observations": [],
            "safety": dict(SAFETY),
        }

    if "plant_id" not in parameters:
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "Existing history provider does not declare plant_id; legacy/global history is blocked.",
            "observations": [],
            "safety": dict(SAFETY),
        }

    rows = provider(plant_id=plant_id, tag=tag)
    if not isinstance(rows, list):
        raise ValueError("tenant predictive history provider must return a list")

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("predictive history rows must be dictionaries")
        row_plant = row.get("plant_id")
        if row_plant is None or str(row_plant) != plant_id:
            raise ValueError("tenant predictive history row has invalid plant scope")
        row_tag = row.get("tag")
        if row_tag is not None and str(row_tag) != tag:
            raise ValueError("predictive history tag mismatch")

    return {
        "plant_id": plant_id,
        "tag": tag,
        "status": "INVOKED",
        "observations": rows,
        "observation_count": len(rows),
        "safety": dict(SAFETY),
    }
