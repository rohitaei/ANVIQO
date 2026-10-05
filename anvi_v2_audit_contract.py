"""ANVIQO V2 audit/observability contract.

Contract only: production persistence/SIEM integration remains a deployment
boundary. Records are tenant scoped, UTC-aware, append-only and contain no
secret-bearing fields by contract.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib, json

@dataclass(frozen=True)
class AuditRecord:
    organization_id: str
    plant_id: str
    actor: str
    action: str
    resource: str
    occurred_at: datetime
    result: str
    correlation_id: str
    safety_flags: dict

    def validate(self) -> "AuditRecord":
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if not all((self.organization_id, self.plant_id, self.actor, self.action,
                    self.resource, self.result, self.correlation_id)):
            raise ValueError("AUDIT_REQUIRED_FIELD_MISSING")
        if not isinstance(self.safety_flags, dict):
            raise ValueError("SAFETY_FLAGS_MUST_BE_OBJECT")
        return self

    @property
    def audit_id(self) -> str:
        self.validate()
        payload = [self.organization_id, self.plant_id, self.actor, self.action,
                   self.resource, self.occurred_at.astimezone(timezone.utc).isoformat(),
                   self.result, self.correlation_id]
        return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()

class AuditLedger:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []
        self._ids: set[str] = set()

    def append(self, record: AuditRecord, organization_id: str, plant_id: str) -> bool:
        record.validate()
        if record.organization_id != organization_id or record.plant_id != plant_id:
            raise PermissionError("TENANT_BOUNDARY_VIOLATION")
        if record.audit_id in self._ids:
            return False
        self._ids.add(record.audit_id)
        self._records.append(record)
        return True

    def query(self, organization_id: str, plant_id: str) -> list[AuditRecord]:
        return [r for r in self._records if r.organization_id == organization_id and r.plant_id == plant_id]

    def snapshot(self) -> dict:
        return {
            "records": len(self._records),
            "append_only": True,
            "tenant_scoped": True,
            "secret_payloads": False,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "automatic_execution": False,
            "human_decision_required": True,
        }
