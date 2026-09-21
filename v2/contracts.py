"""Stable read-only contracts for the V2 data fabric."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class IndustrialPoint:
    plant_id: str
    tag: str
    timestamp: str
    value: Any
    source: str
    mode: str = "UNKNOWN"
    quality: str = "UNKNOWN"
    state: str = "UNKNOWN"
    unit: Optional[str] = None
    description: Optional[str] = None
    area: Optional[str] = None
    io_type: Optional[str] = None
    plc_address: Optional[str] = None
    sequence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def now(plant_id: str, tag: str, value: Any, source: str, **kwargs: Any) -> "IndustrialPoint":
        return IndustrialPoint(
            plant_id=plant_id,
            tag=tag,
            timestamp=datetime.now(timezone.utc).isoformat(),
            value=value,
            source=source,
            **kwargs,
        )

@dataclass(frozen=True)
class FabricHealth:
    status: str
    points_received: int
    last_timestamp: Optional[str]
    source: str
    read_only: bool = True
    plc_write: bool = False
    scada_control: bool = False
    human_decision_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
