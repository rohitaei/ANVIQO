"""Universal V2 orchestration seam: live watch context -> existing V5 What Changed."""
from __future__ import annotations

from typing import Any, Callable, Optional

from .equipment_dna import EquipmentDNAContext
from .event_context import LiveEventContextBridge
from .v5_live_what_changed import run_live_v5_what_changed
from .watch import WatchSnapshot


def run_live_v5_pipeline(
    plant_id: str,
    watch_snapshot: WatchSnapshot,
    equipment_dna: EquipmentDNAContext,
    area_provider: Callable[[str], list[dict[str, Any]]],
    equipment_events: Any = None,
    existing_what_changed: Any = None,
    v5_builder: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Join live watch + tenant DNA, then invoke existing V5 with tenant evidence."""
    if watch_snapshot.plant_id != plant_id:
        raise ValueError("watch snapshot plant_id does not match plant_id")

    context = LiveEventContextBridge().build(
        plant_id,
        watch_snapshot,
        equipment_dna,
        v5_what_changed=existing_what_changed,
    )
    return run_live_v5_what_changed(
        context,
        area_provider,
        equipment_events=equipment_events,
        v5_builder=v5_builder,
    )
