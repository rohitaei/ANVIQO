"""Universal V2 bridge into existing V5 What Changed/Event intelligence.

V2 supplies live evidence/context; V5 remains authoritative for What Changed,
health, equipment reasoning, and event correlation. No V5 reasoning is copied
or reimplemented here.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from .event_context import LiveEventContext


class V5EventIntelligenceBridge:
    """Invoke existing V5 What Changed/Event intelligence with V2 context."""

    def __init__(self, v5_handler: Optional[Callable[..., Any]] = None) -> None:
        self.v5_handler = v5_handler

    def run(self, context: LiveEventContext) -> dict[str, Any]:
        if not isinstance(context, LiveEventContext):
            raise TypeError("context must be LiveEventContext")

        if self.v5_handler is None:
            return self._not_invoked(context)

        result = self.v5_handler(
            plant_id=context.plant_id,
            changed_points=list(context.changed_points),
            equipment_context=list(context.equipment_context),
            existing_what_changed=context.v5_what_changed,
        )

        return {
            "plant_id": context.plant_id,
            "status": "INVOKED",
            "result": result,
            "safety": dict(context.safety),
        }

    @staticmethod
    def _not_invoked(context: LiveEventContext) -> dict[str, Any]:
        return {
            "plant_id": context.plant_id,
            "status": "NOT_INVOKED",
            "reason": "No existing V5 What Changed/Event bridge was supplied.",
            "existing_what_changed": context.v5_what_changed,
            "safety": dict(context.safety),
        }


def bridge_live_event_context(
    context: LiveEventContext,
    v5_handler: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Functional entry point for V2 live-event -> existing V5 integration."""
    return V5EventIntelligenceBridge(v5_handler).run(context)
