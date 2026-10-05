"""ANVIQO V2 time-series contract.

Contract only: no external database is implied. Production adapters may bind this
contract to a durable time-series system later. All data is tenant scoped,
UTC-aware, append-only, deduplicated and read-only.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib, json

QUALITY = {"GOOD", "BAD", "UNCERTAIN"}
MAX_QUERY_WINDOW = timedelta(days=31)

def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
    return value.astimezone(timezone.utc)

def _id(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

@dataclass(frozen=True)
class TimeSeriesPoint:
    organization_id: str
    plant_id: str
    tag: str
    timestamp: datetime
    value: float
    engineering_unit: str | None = None
    quality: str = "GOOD"
    source: str = "V2"
    sequence: int | None = None

    @property
    def point_id(self) -> str:
        return _id([self.organization_id, self.plant_id, self.tag, _utc(self.timestamp).isoformat(), self.value, self.sequence])

    def validate(self) -> "TimeSeriesPoint":
        _utc(self.timestamp)
        if not self.organization_id or not self.plant_id or not self.tag:
            raise ValueError("TENANT_AND_TAG_REQUIRED")
        if self.quality.upper() not in QUALITY:
            raise ValueError("INVALID_QUALITY")
        if not isinstance(self.value, (int, float)):
            raise ValueError("VALUE_MUST_BE_NUMERIC")
        return self

class TimeSeriesStore:
    def __init__(self) -> None:
        self._points: dict[str, TimeSeriesPoint] = {}

    def append(self, point: TimeSeriesPoint, organization_id: str, plant_id: str) -> bool:
        point.validate()
        if point.organization_id != organization_id or point.plant_id != plant_id:
            raise PermissionError("TENANT_BOUNDARY_VIOLATION")
        if point.point_id in self._points:
            return False
        self._points[point.point_id] = point
        return True

    def query(self, organization_id: str, plant_id: str, start: datetime, end: datetime, tag: str | None = None) -> list[TimeSeriesPoint]:
        start, end = _utc(start), _utc(end)
        if end < start:
            raise ValueError("INVALID_QUERY_WINDOW")
        if end - start > MAX_QUERY_WINDOW:
            raise ValueError("QUERY_WINDOW_TOO_LARGE")
        return sorted(
            (p for p in self._points.values()
             if p.organization_id == organization_id and p.plant_id == plant_id
             and start <= _utc(p.timestamp) <= end
             and (tag is None or p.tag == tag)),
            key=lambda p: _utc(p.timestamp),
        )

    def snapshot(self) -> dict:
        return {"points": len(self._points), "append_only": True, "read_only": True,
                "plc_write": False, "scada_control": False, "automatic_execution": False,
                "human_decision_required": True}
