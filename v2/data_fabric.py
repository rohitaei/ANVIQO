"""ANVIQO V2 bounded, plant-scoped, read-only data fabric."""
from collections import defaultdict, deque
from threading import RLock
from typing import Any, Deque, Dict, Iterable, List, Mapping, Optional

from .contracts import FabricHealth, IndustrialPoint

class ReadOnlyDataFabric:
    """Transport-neutral recent-value buffer for V2."""

    def __init__(self, max_points_per_tag: int = 120) -> None:
        if max_points_per_tag < 2:
            raise ValueError("max_points_per_tag must be >= 2")
        self._max_points = int(max_points_per_tag)
        self._lock = RLock()
        self._streams: Dict[str, Dict[str, Deque[IndustrialPoint]]] = defaultdict(dict)
        self._received: Dict[str, int] = defaultdict(int)
        self._last: Dict[str, Optional[str]] = {}
        self._sources: Dict[str, str] = {}

    def ingest(self, point: IndustrialPoint) -> IndustrialPoint:
        if not point.plant_id.strip():
            raise ValueError("plant_id is required")
        if not point.tag.strip():
            raise ValueError("tag is required")
        if not point.source.strip():
            raise ValueError("source is required")
        with self._lock:
            plant = self._streams[point.plant_id]
            stream = plant.setdefault(point.tag, deque(maxlen=self._max_points))
            sequence = self._received[point.plant_id] + 1
            normalized = IndustrialPoint(**{**point.to_dict(), "sequence": sequence})
            stream.append(normalized)
            self._received[point.plant_id] = sequence
            self._last[point.plant_id] = normalized.timestamp
            self._sources[point.plant_id] = normalized.source
            return normalized

    def ingest_many(self, points: Iterable[IndustrialPoint]) -> int:
        count = 0
        for point in points:
            self.ingest(point)
            count += 1
        return count

    def latest(self, plant_id: str, tag: str) -> Optional[IndustrialPoint]:
        with self._lock:
            stream = self._streams.get(plant_id, {}).get(tag)
            return stream[-1] if stream else None

    def history(self, plant_id: str, tag: str, limit: int = 30) -> List[IndustrialPoint]:
        if limit < 1:
            return []
        with self._lock:
            stream = self._streams.get(plant_id, {}).get(tag)
            return list(stream)[-limit:] if stream else []

    def snapshot(self, plant_id: str) -> Dict[str, IndustrialPoint]:
        with self._lock:
            return {
                tag: stream[-1]
                for tag, stream in self._streams.get(plant_id, {}).items()
                if stream
            }

    def health(self, plant_id: str) -> FabricHealth:
        with self._lock:
            return FabricHealth(
                status="LIVE" if self._received.get(plant_id, 0) else "NO_DATA",
                points_received=self._received.get(plant_id, 0),
                last_timestamp=self._last.get(plant_id),
                source=self._sources.get(plant_id, "UNKNOWN"),
            )

def normalize_simulation_point(raw: Mapping[str, Any], plant_id: str) -> IndustrialPoint:
    """Normalize the existing PCI demo observation only."""
    return IndustrialPoint(
        plant_id=plant_id,
        tag=str(raw.get("tag") or "").strip(),
        timestamp=str(raw.get("timestamp") or ""),
        value=raw.get("value"),
        source=str(raw.get("source") or "UNKNOWN"),
        mode=str(raw.get("mode") or "UNKNOWN"),
        quality="GOOD" if raw.get("state") else "UNKNOWN",
        state=str(raw.get("state") or "UNKNOWN"),
        description=raw.get("description"),
        area=raw.get("area"),
        io_type=raw.get("io_type"),
        plc_address=raw.get("plc_address"),
    )
