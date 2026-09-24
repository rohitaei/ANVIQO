"""Universal V2 WATCH-state and discovery orchestration.

This module is an evidence/orchestration layer only. It detects generic
observation changes and evidence-quality conditions, then optionally hands
discovery context to an injected existing-V5 bridge. It does not implement
anomaly detection, prediction, diagnosis, health scoring, alarms, or control.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from .data_trust import DataTrustPolicy
from .data_fabric import ReadOnlyDataFabric


@dataclass(frozen=True)
class WatchCandidate:
    tag: str
    reason: str
    previous_value: Any = None
    current_value: Any = None
    trust: str = "UNKNOWN"
    freshness: str = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "reason": self.reason,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "trust": self.trust,
            "freshness": self.freshness,
        }


@dataclass(frozen=True)
class WatchSnapshot:
    plant_id: str
    state: str
    points_seen: int
    trusted_points: int
    limited_points: int
    untrusted_points: int
    candidates: Tuple[WatchCandidate, ...]
    discovery: Dict[str, Any]
    safety: Dict[str, bool]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plant_id": self.plant_id,
            "state": self.state,
            "points_seen": self.points_seen,
            "trusted_points": self.trusted_points,
            "limited_points": self.limited_points,
            "untrusted_points": self.untrusted_points,
            "candidates": [x.to_dict() for x in self.candidates],
            "discovery": self.discovery,
            "safety": self.safety,
        }


class WatchOrchestrator:
    """Generic WATCH/discovery coordinator around the V2 evidence fabric."""

    def __init__(
        self,
        fabric: ReadOnlyDataFabric,
        trust_policy: Optional[DataTrustPolicy] = None,
        v5_bridge: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.fabric = fabric
        self.trust_policy = trust_policy or DataTrustPolicy()
        self.v5_bridge = v5_bridge
        self._previous: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _changed(previous: Any, current: Any) -> bool:
        if previous is None:
            return False
        return previous != current

    def observe(self, plant_id: str) -> WatchSnapshot:
        plant_id = str(plant_id or "").strip()
        if not plant_id:
            raise ValueError("plant_id is required")

        current = self.fabric.snapshot(plant_id)
        previous = self._previous.get(plant_id, {})

        trusted = limited = untrusted = 0
        candidates = []

        for tag, point in current.items():
            result = self.trust_policy.evaluate(point)
            if result.trust == "TRUSTED":
                trusted += 1
            elif result.trust == "LIMITED":
                limited += 1
            else:
                untrusted += 1

            if result.freshness in ("STALE", "AGING"):
                candidates.append(
                    WatchCandidate(
                        tag=tag,
                        reason="evidence_freshness",
                        current_value=point.value,
                        trust=result.trust,
                        freshness=result.freshness,
                    )
                )
            elif result.trust in ("DEGRADED", "LIMITED"):
                candidates.append(
                    WatchCandidate(
                        tag=tag,
                        reason="evidence_quality",
                        current_value=point.value,
                        trust=result.trust,
                        freshness=result.freshness,
                    )
                )

            if self._changed(previous.get(tag), point.value):
                candidates.append(
                    WatchCandidate(
                        tag=tag,
                        reason="value_changed_since_previous_observation",
                        previous_value=previous.get(tag),
                        current_value=point.value,
                        trust=result.trust,
                        freshness=result.freshness,
                    )
                )

        self._previous[plant_id] = {
            tag: point.value for tag, point in current.items()
        }

        if not current or trusted == 0:
            state = "INSUFFICIENT_EVIDENCE"
        elif candidates:
            state = "WATCH"
        else:
            state = "OBSERVE"

        discovery = {
            "status": "CANDIDATES_IDENTIFIED" if candidates else "NO_GENERIC_TRIGGER",
            "candidate_count": len(candidates),
            "meaning": (
                "Candidates require existing V5 intelligence or human "
                "investigation; V2 does not classify them as anomalies."
            ),
            "v5": {"status": "NOT_INVOKED"},
        }

        return WatchSnapshot(
            plant_id=plant_id,
            state=state,
            points_seen=len(current),
            trusted_points=trusted,
            limited_points=limited,
            untrusted_points=untrusted,
            candidates=tuple(candidates),
            discovery=discovery,
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
            return snapshot

        try:
            result = self.v5_bridge(
                plant_id=plant_id,
                discovery=snapshot,
            )
            snapshot["discovery"]["v5"] = {
                "status": "INVOKED",
                "result": result,
            }
        except Exception as exc:
            snapshot["discovery"]["v5"] = {
                "status": "ERROR",
                "error": str(exc),
            }

        return snapshot
