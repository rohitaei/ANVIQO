"""V2 replay/correlation bridge over the append-only real-time evidence store.

It deliberately returns evidence and temporal association, not causal claims.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from anvi_v2_realtime_store import InMemoryRealtimeStore


def replay_window(
    store: InMemoryRealtimeStore,
    organization_id: str,
    plant_id: str,
    start: datetime,
    end: datetime,
    tag: Optional[str] = None,
) -> dict:
    points = store.query_points(
        organization_id, plant_id, tag=tag, start=start, end=end
    )
    events = [
        e for e in store.query_events(organization_id, plant_id)
        if start <= e.timestamp <= end
    ]
    timeline = [
        {
            "kind": "TELEMETRY",
            "timestamp": p.timestamp.isoformat(),
            "tag": p.tag,
            "value": p.value,
            "quality": p.quality,
            "source": p.source,
            "evidence_id": p.observation_id,
        }
        for p in points
    ]
    timeline.extend(
        {
            "kind": "EVENT",
            "timestamp": e.timestamp.isoformat(),
            "event_type": e.event_type,
            "tag": e.tag,
            "equipment": e.equipment,
            "message": e.message,
            "severity": e.severity,
            "source": e.source,
            "evidence_id": e.event_id,
        }
        for e in events
    )
    timeline.sort(key=lambda row: row["timestamp"])
    return {
        "organization_id": organization_id,
        "plant_id": plant_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timeline": timeline,
        "evidence_count": len(timeline),
        "causation_claimed": False,
        "safety": {
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_decision_required": True,
        },
    }
