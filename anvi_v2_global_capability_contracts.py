"""ANVIQO Global V2 universal capability contracts.

Shared, tenant-safe interfaces for the complete V2 roadmap. These contracts
provide deterministic validation and integration boundaries; they do not
pretend that an external OT/CMMS/SSO/model backend is connected.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}

def _aware(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("timestamp must have timezone")
    return ts.astimezone(timezone.utc)

@dataclass(frozen=True)
class TenantRef:
    organization_id: str
    plant_id: str

@dataclass(frozen=True)
class AuditRecord:
    tenant: TenantRef
    actor_id: str
    action: str
    timestamp: datetime
    outcome: str
    correlation_id: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        _aware(self.timestamp)
        if not self.tenant.organization_id or not self.tenant.plant_id:
            raise ValueError("tenant is required")
        if not self.actor_id or not self.action or not self.correlation_id:
            raise ValueError("audit identity/action/correlation is required")

@dataclass(frozen=True)
class PredictionValidation:
    tenant: TenantRef
    model_id: str
    prediction_id: str
    predicted_at: datetime
    horizon_seconds: int
    confidence: float
    actual_available: bool
    actual_value: float | None = None
    predicted_value: float | None = None

    def validate(self) -> None:
        _aware(self.predicted_at)
        if not self.model_id or not self.prediction_id:
            raise ValueError("model and prediction IDs are required")
        if self.horizon_seconds < 0 or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("invalid prediction validation values")

@dataclass(frozen=True)
class EvidenceNode:
    tenant: TenantRef
    node_id: str
    node_type: str
    label: str
    observed_at: datetime
    source: str

@dataclass(frozen=True)
class CausalEdge:
    tenant: TenantRef
    from_node: str
    to_node: str
    relation: str
    confidence: float
    evidence_ids: tuple[str, ...] = ()

    def validate(self) -> None:
        _aware(self.tenant and datetime.now(timezone.utc))
        if not self.from_node or not self.to_node or not self.relation:
            raise ValueError("causal edge endpoints/relation are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("causal confidence must be 0..1")

@dataclass(frozen=True)
class DigitalTwinState:
    tenant: TenantRef
    asset_id: str
    timestamp: datetime
    state: Mapping[str, Any]
    source: str

@dataclass(frozen=True)
class WhatIfScenario:
    tenant: TenantRef
    scenario_id: str
    inputs: Mapping[str, Any]
    outputs: Mapping[str, Any]
    assumptions: tuple[str, ...] = ()

@dataclass(frozen=True)
class IntegrationRequest:
    tenant: TenantRef
    system: str
    operation: str
    payload: Mapping[str, Any]
    dry_run: bool = True

@dataclass(frozen=True)
class ResilienceCheck:
    name: str
    passed: bool
    evidence: tuple[str, ...] = ()

@dataclass(frozen=True)
class OutcomeRecord:
    tenant: TenantRef
    outcome_id: str
    decision_id: str
    result: str
    recorded_at: datetime
    human_verified: bool

@dataclass(frozen=True)
class BenchmarkRecord:
    tenant: TenantRef
    metric: str
    value: float
    period: str

def assert_tenant(request_tenant: TenantRef, selected: TenantRef) -> None:
    if request_tenant != selected:
        raise PermissionError("CROSS_TENANT_ACCESS_BLOCKED")

def safety_contract() -> dict[str, bool]:
    return dict(SAFETY)

def validate_v2_object(obj: Any) -> dict[str, Any]:
    validator = getattr(obj, "validate", None)
    if callable(validator):
        validator()
    return {"valid": True, "safety": safety_contract()}

def capability_surface() -> dict[str, str]:
    return {
        "telemetry_time_series": "contracted",
        "evidence_graph": "contracted",
        "edge_connectors": "contracted",
        "event_correlation": "contracted",
        "prediction_validation": "contracted",
        "enterprise_identity": "contracted",
        "audit_observability": "contracted",
        "multi_plant_command_centre": "contracted",
        "api_connector_registry": "contracted",
        "causal_root_cause": "contracted",
        "digital_twin": "contracted",
        "energy_production_quality": "contracted",
        "optimization_what_if": "contracted",
        "cmms_eam_sap": "adapter_boundary",
        "android_client": "client_boundary",
        "ha_dr_load": "certification_boundary",
        "outcome_learning": "contracted",
        "fleet_benchmarking": "tenant_scoped",
        "advanced_replay": "implemented",
        "global_management": "contracted",
    }
