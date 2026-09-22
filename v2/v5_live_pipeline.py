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

def run_live_v5_pipeline_with_tenant_evidence(
    plant_id: str,
    watch_snapshot: WatchSnapshot,
    equipment_dna: EquipmentDNAContext,
    evidence_provider: Callable[[str], list[dict[str, Any]]],
    equipment_events: Any = None,
    existing_what_changed: Any = None,
    v5_builder: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Run the live V2→V5 pipeline using a tenant-scoped evidence provider.

    The provider is called only with the requested plant_id; no global or
    cross-plant evidence fallback is permitted.
    """
    if not callable(evidence_provider):
        raise TypeError("evidence_provider must be callable")
    return run_live_v5_pipeline(
        plant_id,
        watch_snapshot,
        equipment_dna,
        evidence_provider,
        equipment_events=equipment_events,
        existing_what_changed=existing_what_changed,
        v5_builder=v5_builder,
    )
