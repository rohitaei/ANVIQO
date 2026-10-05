"""V2 append-only real-time evidence/time-series foundation.

This is a protocol-neutral storage contract for the V2 development branch.
It is intentionally independent of V1 production runtime and makes no PLC or
SCADA write calls. A production deployment can replace the in-memory backend
with PostgreSQL/TimescaleDB or another approved time-series implementation
without changing the normalized contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Dict, Iterable, List, Optional, Tuple


EVENT_TYPES = {
    "ALARM",
    "STATE_CHANGE",
    "LIMIT_BREACH",
    "QUALITY_CHANGE",
    "CONNECTIVITY",
    "MAINTENANCE",
    "OPERATOR_EVENT",
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class TelemetryPoint:
    organization_id: str
    plant_id: str
    tag: str
    timestamp: datetime
    value: object
    engineering_unit: str = ""
    quality: str = "GOOD"
    source: str = "UNKNOWN"
    sequence: Optional[int] = None

    @property
    def observation_id(self) -> str:
        raw = "|".join(
            [
                self.organization_id,
                self.plant_id,
                self.tag,
                _utc(self.timestamp).isoformat(),
                str(self.sequence) if self.sequence is not None else "",
                self.source,
            ]
        )
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StreamEvent:
    organization_id: str
    plant_id: str
    event_type: str
    timestamp: datetime
    message: str
    tag: str = ""
    equipment: str = ""
    severity: str = "INFO"
    source: str = "UNKNOWN"
    event_id: Optional[str] = None

    def normalized(self) -> "StreamEvent":
        kind = self.event_type.strip().upper()
        if kind not in EVENT_TYPES:
            raise ValueError(f"unsupported event_type: {kind}")
        ts = _utc(self.timestamp)
        event_id = self.event_id or sha256(
            "|".join(
                [
                    self.organization_id,
                    self.plant_id,
                    kind,
                    ts.isoformat(),
                    self.tag,
                    self.equipment,
                    self.message,
                    self.source,
                ]
            ).encode("utf-8")
        ).hexdigest()
        return StreamEvent(
            self.organization_id,
            self.plant_id,
            kind,
            ts,
            self.message.strip(),
            self.tag.strip(),
            self.equipment.strip(),
            self.severity.strip().upper(),
            self.source.strip(),
            event_id,
        )


class InMemoryRealtimeStore:
    """Deterministic reference backend used for V2 contract tests and demos."""

    def __init__(self) -> None:
        self._points: Dict[str, TelemetryPoint] = {}
        self._events: Dict[str, StreamEvent] = {}

    @staticmethod
    def _scope(organization_id: str, plant_id: str) -> Tuple[str, str]:
        return organization_id.strip(), plant_id.strip()

    def append_point(self, point: TelemetryPoint) -> str:
        if not point.organization_id or not point.plant_id or not point.tag:
            raise ValueError("organization_id, plant_id and tag are required")
        _utc(point.timestamp)
        self._points.setdefault(point.observation_id, point)
        return point.observation_id

    def append_event(self, event: StreamEvent) -> str:
        normalized = event.normalized()
        if not normalized.organization_id or not normalized.plant_id:
            raise ValueError("organization_id and plant_id are required")
        self._events.setdefault(normalized.event_id, normalized)
        return normalized.event_id

    def query_points(
        self,
        organization_id: str,
        plant_id: str,
        tag: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[TelemetryPoint]:
        org, plant = self._scope(organization_id, plant_id)
        if start:
            start = _utc(start)
        if end:
            end = _utc(end)
        rows = [
            p for p in self._points.values()
            if p.organization_id == org
            and p.plant_id == plant
            and (tag is None or p.tag == tag)
            and (start is None or _utc(p.timestamp) >= start)
            and (end is None or _utc(p.timestamp) <= end)
        ]
        return sorted(rows, key=lambda p: _utc(p.timestamp))

    def query_events(
        self,
        organization_id: str,
        plant_id: str,
        event_type: Optional[str] = None,
    ) -> List[StreamEvent]:
        org, plant = self._scope(organization_id, plant_id)
        kind = event_type.strip().upper() if event_type else None
        rows = [
            e for e in self._events.values()
            if e.organization_id == org
            and e.plant_id == plant
            and (kind is None or e.event_type == kind)
        ]
        return sorted(rows, key=lambda e: _utc(e.timestamp))

    def snapshot(self) -> dict:
        return {
            "telemetry_points": len(self._points),
            "events": len(self._events),
            "write_capability": False,
            "plc_write": False,
            "scada_control": False,
        }
