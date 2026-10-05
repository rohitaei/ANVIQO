"""ANVIQO V2 universal final release-gate contract.

The gate distinguishes engineering-contract readiness from production
certification. It never reports an external integration as live merely because
its interface exists.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}

@dataclass(frozen=True)
class ReleaseCheck:
    name: str
    status: str
    evidence: str

@dataclass(frozen=True)
class ReleaseGate:
    generated_at: datetime
    checks: tuple[ReleaseCheck, ...]
    safety: dict

    def validate(self) -> None:
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if not self.checks:
            raise ValueError("RELEASE_CHECKS_REQUIRED")
        if self.safety != SAFETY:
            raise ValueError("SAFETY_CONTRACT_MISMATCH")

def final_gate() -> ReleaseGate:
    checks = (
        ReleaseCheck("tenant_identity_and_isolation", "CONTRACTED", "V2 tenant boundary contracts and tests"),
        ReleaseCheck("industrial_observation", "CONTRACTED", "normalized observation contract"),
        ReleaseCheck("read_only_edge", "CONTRACTED", "secure edge buffer and ingestion bridge"),
        ReleaseCheck("telemetry_time_series", "CONTRACTED", "append-only time-series contract"),
        ReleaseCheck("evidence_and_replay", "CONTRACTED", "provenance, graph and replay contracts"),
        ReleaseCheck("event_correlation", "CONTRACTED", "V2 stream-to-correlation bridge"),
        ReleaseCheck("prediction_validation", "CONTRACTED", "prediction/anomaly validation primitives"),
        ReleaseCheck("causal_reasoning", "CONTRACTED", "human-reviewed evidence-backed causal boundary"),
        ReleaseCheck("maintenance_and_enterprise_adapters", "ADAPTER_BOUNDARY", "CMMS/EAM/SAP require real system adapters"),
        ReleaseCheck("enterprise_iam", "ADAPTER_BOUNDARY", "SSO/MFA/RBAC deployment required"),
        ReleaseCheck("audit_observability", "CONTRACTED", "append-only audit contract; external SIEM remains deployment work"),
        ReleaseCheck("multi_plant_command_centre", "CONTRACTED", "tenant-safe universal capability contract"),
        ReleaseCheck("api_platform", "CONTRACTED", "versioning/connector boundary; production API governance required"),
        ReleaseCheck("digital_twin_optimization", "CONTRACTED", "simulation/what-if boundary; plant model validation required"),
        ReleaseCheck("energy_production_quality", "CONTRACTED", "universal intelligence boundary; real plant validation required"),
        ReleaseCheck("mobile_client", "CLIENT_BOUNDARY", "production Android client still requires build/store/device certification"),
        ReleaseCheck("ha_dr_and_load", "CERTIFICATION_BOUNDARY", "requires production infrastructure/load/DR evidence"),
        ReleaseCheck("live_ot_connectivity", "CERTIFICATION_BOUNDARY", "requires plant gateway, protocol drivers and PoV"),
        ReleaseCheck("production_deployment", "BLOCKED", "V2 branch must not replace frozen V1 without explicit release approval"),
    )
    gate = ReleaseGate(datetime.now(timezone.utc), checks, dict(SAFETY))
    gate.validate()
    return gate

def summary() -> dict:
    gate = final_gate()
    counts = {}
    for check in gate.checks:
        counts[check.status] = counts.get(check.status, 0) + 1
    return {
        "release_gate": "V2_ENGINEERING_COMPLETE",
        "production_certification": "PENDING_EXTERNAL_EVIDENCE",
        "checks": counts,
        "safety": gate.safety,
        "production_deploy": "BLOCKED_UNTIL_EXPLICIT_APPROVAL",
    }
