"""Deterministic read-only PT pressure demonstration harness.

Uses explicit evidence and a supplied verified-history callback. It is a demo
orchestration seam, not a plant-specific reasoning engine.
"""
from __future__ import annotations
from typing import Any, Callable, Optional
from .alarm_bridge import SAFETY
from .tenant_evidence import TenantEvidenceProvider
from .v5_live_pipeline import run_live_v5_pipeline_with_tenant_evidence
from .watch import WatchSnapshot

def run_pt_pressure_demo(
    plant_id: str,
    watch_snapshot: WatchSnapshot,
    equipment_dna: Any,
    package: dict[str, Any],
    verified_history: Callable[[str, str], Any],
    v5_builder: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    provider=TenantEvidenceProvider(package)
    if provider.plant_id != plant_id:
        raise ValueError("tenant evidence package does not match plant_id")
    v5=run_live_v5_pipeline_with_tenant_evidence(
        plant_id, watch_snapshot, equipment_dna, provider, v5_builder=v5_builder
    )
    history=verified_history(plant_id, "PT-303")
    return {
        "plant_id":plant_id,
        "tag":"PT-303",
        "live_pipeline":v5,
        "verified_history":history,
        "human_verification_required":True,
        "safety":dict(SAFETY),
    }
