"""ANVIQO Global V2 shared industrial contracts.

This module is intentionally protocol-neutral. It validates normalized observations,
evidence provenance and safety boundaries without opening any PLC/SCADA write path.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}

SUPPORTED_PROTOCOLS = {"S7", "OPC_UA", "MQTT", "SPARKPLUG", "MODBUS_TCP", "FILE", "API"}

@dataclass(frozen=True)
class Observation:
    organization_id: str
    plant_id: str
    tag: str
    timestamp: str
    value: Any
    quality: str = "UNKNOWN"
    unit: str = ""
    source_protocol: str = "API"
    source_address: str = ""
    area: str = ""
    equipment: str = ""
    sequence: int | None = None

    def validate(self) -> dict[str, Any]:
        errors = []
        if not self.organization_id: errors.append("organization_id_required")
        if not self.plant_id: errors.append("plant_id_required")
        if not self.tag: errors.append("tag_required")
        if not self.timestamp: errors.append("timestamp_required")
        if self.source_protocol.upper() not in SUPPORTED_PROTOCOLS:
            errors.append("unsupported_source_protocol")
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except Exception:
            errors.append("timestamp_must_be_iso8601")
        return {"valid": not errors, "errors": errors, "safety": SAFETY}

@dataclass(frozen=True)
class Evidence:
    organization_id: str
    plant_id: str
    evidence_type: str
    source: str
    observed_at: str
    content: dict[str, Any]
    confidence: str = "UNKNOWN"

    def validate(self) -> dict[str, Any]:
        errors = []
        if not self.organization_id: errors.append("organization_id_required")
        if not self.plant_id: errors.append("plant_id_required")
        if not self.source: errors.append("source_required")
        if not self.evidence_type: errors.append("evidence_type_required")
        return {"valid": not errors, "errors": errors, "safety": SAFETY}

def normalize_observation(**kwargs) -> dict[str, Any]:
    row = Observation(**kwargs)
    result = row.validate()
    result["observation"] = asdict(row) if result["valid"] else None
    return result

def assert_tenant(organization_id: str, plant_id: str, selected_organization_id: str, selected_plant_id: str) -> None:
    if str(organization_id) != str(selected_organization_id):
        raise PermissionError("FOREIGN_ORGANIZATION_EVIDENCE_BLOCKED")
    if str(plant_id) != str(selected_plant_id):
        raise PermissionError("FOREIGN_PLANT_EVIDENCE_BLOCKED")

def safety_contract() -> dict[str, Any]:
    return dict(SAFETY)
