"""V2 evidence-to-event correlation adapter.

Converts normalized V2 stream events into the existing generic event
correlation engine without changing that V1 engine or adding plant-specific
causal rules.
"""

from __future__ import annotations

from typing import Iterable

from event_correlation import correlate_events
from anvi_v2_realtime_store import StreamEvent


def correlate_stream_events(equipment_tag: str, events: Iterable[StreamEvent]) -> dict:
    rows = []
    for event in events or []:
        normalized = event.normalized()
        rows.append(
            {
                "event_id": normalized.event_id,
                "organization_id": normalized.organization_id,
                "plant_id": normalized.plant_id,
                "timestamp": normalized.timestamp.isoformat(),
                "event_type": normalized.event_type,
                "message": normalized.message,
                "tag": normalized.tag,
                "equipment": normalized.equipment,
                "severity": normalized.severity,
                "source": normalized.source,
            }
        )
    result = correlate_events(equipment_tag, rows)
    result["source_contract"] = "ANVIQO_V2_STREAM_EVENT"
    result["causation_claimed"] = False
    return result
