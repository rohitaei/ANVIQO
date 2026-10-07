"""V2 universal integration boundary; external actions default to dry-run."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any

READ_ONLY_SYSTEMS = {"S7", "OPC_UA", "MQTT", "SPARKPLUG", "MODBUS_TCP", "FILE", "API", "CMMS", "EAM", "SAP", "SSO"}

@dataclass(frozen=True)
class IntegrationEnvelope:
    tenant: object
    system: str
    operation: str
    payload: Mapping[str, Any]
    dry_run: bool = True
    def validate(self) -> None:
        if self.system.upper() not in READ_ONLY_SYSTEMS: raise ValueError("unsupported integration system")
        if not self.operation: raise ValueError("operation is required")
        if not isinstance(self.payload, Mapping): raise ValueError("payload must be a mapping")
        if self.system.upper() in {"S7", "OPC_UA", "MQTT", "SPARKPLUG", "MODBUS_TCP"} and not self.dry_run:
            raise PermissionError("OT_WRITE_PATH_BLOCKED")

def dispatch(envelope: IntegrationEnvelope) -> dict[str, Any]:
    envelope.validate()
    return {"accepted": True, "system": envelope.system.upper(), "operation": envelope.operation,
            "dry_run": envelope.dry_run, "automatic_execution": False, "human_decision_required": True}
