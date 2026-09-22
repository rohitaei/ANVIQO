"""Universal V2 live Plant Brain orchestration.

The Plant Brain is an orchestration/context layer. It collects live evidence,
applies trust metadata, and hands trusted context to the existing V5
intelligence through an injected bridge. It does not implement prediction,
diagnosis, health scoring, alarm decisions, or control.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .data_fabric import ReadOnlyDataFabric
from .data_trust import DataTrustPolicy
from .contracts import IndustrialPoint


@dataclass(frozen=True)
class PlantBrainSnapshot:
    plant_id: str
    points_seen: int
    trusted_points: int
    limited_points: int
    untrusted_points: int
    fresh_points: int
    stale_points: int
    evidence: Dict[str, Dict[str, Any]]
    fabric_health: Dict[str, Any]
    safety: Dict[str, bool]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plant_id": self.plant_id,
            "points_seen": self.points_seen,
            "trusted_points": self.trusted_points,
            "limited_points": self.limited_points,
            "untrusted_points": self.untrusted_points,
            "fresh_points": self.fresh_points,
            "stale_points": self.stale_points,
            "evidence": self.evidence,
            "fabric_health": self.fabric_health,
            "safety": self.safety,
        }


class LivePlantBrain:
    """Universal live-evidence orchestrator for exactly one tenant/plant."""

    def __init__(
        self,
        fabric: ReadOnlyDataFabric,
        trust_policy: Optional[DataTrustPolicy] = None,
        v5_bridge: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.fabric = fabric
        self.trust_policy = trust_policy or DataTrustPolicy()
        self.v5_bridge = v5_bridge

    def observe(self, plant_id: str) -> PlantBrainSnapshot:
        plant_id = str(plant_id or "").strip()
        if not plant_id:
            raise ValueError("plant_id is required")

        points = list(self.fabric.snapshot(plant_id).values())
        evidence: Dict[str, Dict[str, Any]] = {}
        trusted = limited = untrusted = fresh = stale = 0

        for point in points:
            result = self.trust_policy.evaluate(point)
            evidence[point.tag] = {
                "point": point.to_dict(),
                "trust": result.to_dict(),
            }
            if result.trust == "TRUSTED":
                trusted += 1
            elif result.trust == "LIMITED":
                limited += 1
            else:
                untrusted += 1
            if result.freshness == "FRESH":
                fresh += 1
            elif result.freshness == "STALE":
                stale += 1

        return PlantBrainSnapshot(
            plant_id=plant_id,
            points_seen=len(points),
            trusted_points=trusted,
            limited_points=limited,
            untrusted_points=untrusted,
            fresh_points=fresh,
            stale_points=stale,
            evidence=evidence,
            fabric_health=self.fabric.health(plant_id).to_dict(),
            safety={
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "automatic_action": False,
                "human_decision_required": True,
            },
        )

    def run_once(self, plant_id: str) -> Dict[str, Any]:
        snapshot = self.observe(plant_id).to_dict()
        if self.v5_bridge is None:
            snapshot["v5"] = {
                "status": "NOT_INVOKED",
                "reason": "No V5 bridge was supplied; observation remains evidence-only.",
            }
            return snapshot

        # The bridge is deliberately injected. V2 owns orchestration, while
        # existing V5 owns intelligence. This prevents a second reasoning path.
        try:
            result = self.v5_bridge(plant_id=plant_id, evidence=snapshot)
            snapshot["v5"] = {
                "status": "INVOKED",
                "result": result,
            }
        except Exception as exc:
            snapshot["v5"] = {
                "status": "ERROR",
                "error": str(exc),
            }
        return snapshot
