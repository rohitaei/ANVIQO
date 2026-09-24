"""Universal V2 live-event context bridge.

Connects live WATCH evidence to Equipment DNA and accepts existing V5
What Changed/event intelligence as an injected result.

This module is orchestration/context only:
- no second prediction, alarm, root-cause, or health engine
- no plant-specific thresholds or tags
- tenant-scoped
- read-only / human-governed
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LiveEventContext:
    plant_id: str
    state: str
    changed_points: list[dict[str, Any]]
    equipment_context: list[dict[str, Any]]
    v5_what_changed: Any
    safety: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plant_id": self.plant_id,
            "state": self.state,
            "changed_points": list(self.changed_points),
            "equipment_context": list(self.equipment_context),
            "v5_what_changed": self.v5_what_changed,
            "safety": dict(self.safety),
        }


class LiveEventContextBridge:
    """Join generic live changes with tenant-scoped Equipment DNA context."""

    def build(
        self,
        plant_id: str,
        watch_snapshot: Any,
        equipment_dna: Any,
        v5_what_changed: Any = None,
    ) -> LiveEventContext:
        if not isinstance(plant_id, str) or not plant_id.strip():
            raise ValueError("plant_id is required")

        candidates = getattr(watch_snapshot, "candidates", None)
        if candidates is None and isinstance(watch_snapshot, dict):
            candidates = watch_snapshot.get("candidates", [])
        candidates = candidates or []

        state = getattr(watch_snapshot, "state", None)
        if state is None and isinstance(watch_snapshot, dict):
            state = watch_snapshot.get("state", "INSUFFICIENT_EVIDENCE")
        state = str(state or "INSUFFICIENT_EVIDENCE")

        changed_points = []
        equipment_context = []

        for candidate in candidates:
            tag = self._value(candidate, "tag")
            if not tag:
                continue

            item = {
                "tag": tag,
                "reason": self._value(candidate, "reason"),
                "trust": self._value(candidate, "trust"),
                "freshness": self._value(candidate, "freshness"),
                "previous_value": self._value(candidate, "previous_value"),
                "current_value": self._value(candidate, "current_value"),
                "evidence_status": "LIVE_WATCH_CANDIDATE",
            }
            changed_points.append(item)

            context = self._dna_context(equipment_dna, plant_id, tag)
            if context is not None:
                equipment_context.append({
                    "tag": tag,
                    "context": context,
                    "evidence_status": "EQUIPMENT_DNA_CONTEXT",
                })
            else:
                equipment_context.append({
                    "tag": tag,
                    "context": None,
                    "evidence_status": "NO_EQUIPMENT_DNA_CONTEXT",
                })

        return LiveEventContext(
            plant_id=plant_id,
            state=state,
            changed_points=changed_points,
            equipment_context=equipment_context,
            v5_what_changed=v5_what_changed,
            safety={
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "automatic_action": False,
                "human_decision_required": True,
            },
        )

    @staticmethod
    def _value(item: Any, key: str) -> Any:
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    @staticmethod
    def _dna_context(dna: Any, plant_id: str, tag: str) -> Any:
        if dna is None:
            return None
        context_fn = getattr(dna, "context", None)
        if context_fn is None:
            return None
        try:
            result = context_fn(plant_id, tag)
        except (KeyError, ValueError):
            return None
        if not isinstance(result, dict):
            return None
        if result.get("evidence_status") != "FOUND":
            return None
        return result
