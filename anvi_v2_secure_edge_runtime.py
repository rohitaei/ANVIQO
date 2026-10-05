"""ANVIQO V2 secure edge runtime contract.

Protocol-neutral contract/simulation boundary. This does not claim that live
S7/OPC UA/MQTT/Modbus drivers are connected.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import deque

@dataclass(frozen=True)
class EdgeEnvelope:
    organization_id: str
    plant_id: str
    protocol: str
    sequence: int
    observed_at: datetime
    payload: dict

    def validate(self) -> "EdgeEnvelope":
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if self.sequence < 0:
            raise ValueError("SEQUENCE_MUST_BE_NONNEGATIVE")
        if not self.organization_id or not self.plant_id or not self.protocol:
            raise ValueError("EDGE_IDENTITY_REQUIRED")
        return self

class SecureEdgeBuffer:
    def __init__(self) -> None:
        self._buffer = deque()
        self._seen: set[tuple[str, str, int]] = set()
        self._connected = False

    def set_connected(self, connected: bool) -> None:
        self._connected = bool(connected)

    def receive(self, envelope: EdgeEnvelope, organization_id: str, plant_id: str) -> bool:
        envelope.validate()
        if envelope.organization_id != organization_id or envelope.plant_id != plant_id:
            raise PermissionError("TENANT_BOUNDARY_VIOLATION")
        key = (envelope.organization_id, envelope.plant_id, envelope.sequence)
        if key in self._seen:
            return False
        self._seen.add(key)
        self._buffer.append(envelope)
        return True

    def drain(self, organization_id: str, plant_id: str) -> list[EdgeEnvelope]:
        selected, retained = [], deque()
        for envelope in self._buffer:
            if envelope.organization_id == organization_id and envelope.plant_id == plant_id:
                selected.append(envelope)
            else:
                retained.append(envelope)
        self._buffer = retained
        return sorted(selected, key=lambda x: (x.observed_at.astimezone(timezone.utc), x.sequence))

    def control_surface(self) -> dict:
        return {
            "outbound_only": True,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "automatic_execution": False,
            "human_decision_required": True,
        }
