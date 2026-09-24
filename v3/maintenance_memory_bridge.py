"""V3 tenant-safe bridge for existing maintenance memory.

This module is retrieval orchestration only. It never infers causation,
failure probability, RUL, diagnosis, or control actions.
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


def fetch_tenant_maintenance_memory(
    plant_id: str,
    tag: str,
    provider: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Fetch maintenance memory only from an explicitly tenant-scoped provider."""
    plant_id = str(plant_id or "").strip()
    tag = str(tag or "").strip()
    if not plant_id or not tag:
        raise ValueError("plant_id and tag are required")

    if provider is None:
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "No existing tenant-scoped maintenance memory provider was supplied.",
            "records": [],
            "safety": dict(SAFETY),
        }

    try:
        parameters = inspect.signature(provider).parameters
    except (TypeError, ValueError):
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "Maintenance memory provider signature could not be verified as tenant-aware.",
            "records": [],
            "safety": dict(SAFETY),
        }

    if "plant_id" not in parameters:
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "Existing maintenance memory provider does not declare plant_id; legacy/global memory is blocked.",
            "records": [],
            "safety": dict(SAFETY),
        }

    rows = provider(plant_id=plant_id, tag=tag)
    if not isinstance(rows, list):
        raise ValueError("tenant maintenance memory provider must return a list")

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("maintenance memory rows must be dictionaries")
        row_plant = row.get("plant_id")
        if row_plant is None or str(row_plant) != plant_id:
            raise ValueError("tenant maintenance memory row has invalid plant scope")
        row_tag = row.get("tag")
        if row_tag is not None and str(row_tag) != tag:
            raise ValueError("maintenance memory tag mismatch")

    return {
        "plant_id": plant_id,
        "tag": tag,
        "status": "INVOKED",
        "records": rows,
        "record_count": len(rows),
        "safety": dict(SAFETY),
    }
