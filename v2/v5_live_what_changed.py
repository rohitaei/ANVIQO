"""Tenant-scoped bridge from V2 live context to the existing V5 area evidence.

V2 does not recreate plant-health or What Changed reasoning. A caller supplies
an already tenant-scoped area-evidence provider; this adapter validates the
tenant boundary and forwards that evidence to the existing V5 builder.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from .event_context import LiveEventContext
from .v5_what_changed import run_existing_v5_what_changed


def run_live_v5_what_changed(
    context: LiveEventContext,
    area_provider: Callable[[str], list[dict[str, Any]]],
    equipment_events: Any = None,
    v5_builder: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Build tenant-scoped V5 evidence through an explicitly supplied provider."""
    if not isinstance(context, LiveEventContext):
        raise TypeError("context must be LiveEventContext")
    if not callable(area_provider):
        raise TypeError("area_provider must be callable")

    area_results = area_provider(context.plant_id)
    if not isinstance(area_results, list):
        raise TypeError("area_provider must return a list")

    # Never repair, substitute, or globally fall back on tenant identity.
    for area in area_results:
        if not isinstance(area, dict):
            raise TypeError("each area result must be a dict")
        if area.get("plant_id") != context.plant_id:
            raise ValueError(
                "area provider returned evidence for a different plant"
            )

    return run_existing_v5_what_changed(
        context,
        area_results,
        equipment_events=equipment_events,
        v5_builder=v5_builder,
    )
