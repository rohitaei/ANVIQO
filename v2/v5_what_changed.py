"""Safe adapter from V2 tenant-scoped live context to V5 What Changed.

The adapter calls the existing V5 build_plant_what_changed function.
It adds no health, anomaly, event-correlation, prediction, or diagnosis logic.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from .event_context import LiveEventContext


def run_existing_v5_what_changed(
    context: LiveEventContext,
    area_results: list[dict[str, Any]],
    equipment_events: Any = None,
    v5_builder: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Invoke the existing V5 builder using explicitly tenant-scoped evidence."""
    if not isinstance(context, LiveEventContext):
        raise TypeError("context must be LiveEventContext")
    if not isinstance(area_results, list):
        raise TypeError("area_results must be a list")

    for area in area_results:
        if not isinstance(area, dict):
            raise TypeError("each area result must be a dict")
        evidence_plant_id = area.get("plant_id")
        if evidence_plant_id != context.plant_id:
            raise ValueError(
                "area evidence plant_id does not match live context plant_id"
            )

    if v5_builder is None:
        from plant_what_changed import build_plant_what_changed
        v5_builder = build_plant_what_changed

    result = v5_builder(
        context.plant_id,
        area_results,
        equipment_events=equipment_events,
    )

    return {
        "plant_id": context.plant_id,
        "status": "V5_WHAT_CHANGED_COMPLETE",
        "result": result,
        "safety": dict(context.safety),
    }
