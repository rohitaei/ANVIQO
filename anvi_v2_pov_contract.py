"""ANVIQO V2 controlled Plant PoV readiness contract.

This module is a governance/acceptance contract. It does not connect to a PLC
and does not claim that a live plant integration is certified.
"""

from dataclasses import dataclass
from typing import Dict

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


@dataclass(frozen=True)
class PovGate:
    name: str
    status: str
    evidence_required: bool = True


REQUIRED_GATES = (
    "plant_identity",
    "read_only_edge",
    "telemetry_quality",
    "evidence_traceability",
    "event_correlation",
    "anomaly_prediction_validation",
    "maintenance_review",
    "tenant_isolation",
    "audit_governance",
    "security_review",
    "outcome_measurement",
    "second_plant_repeatability",
)


def pov_gate_status(evidence: Dict[str, bool]) -> Dict[str, object]:
    """Evaluate readiness without pretending missing external evidence exists."""
    gates = []
    for name in REQUIRED_GATES:
        passed = bool(evidence.get(name, False))
        gates.append(PovGate(name=name, status="PASS" if passed else "PENDING"))
    ready = all(g.status == "PASS" for g in gates)
    return {
        "pov_ready": ready,
        "gates": [g.__dict__ for g in gates],
        "production_deploy": "BLOCKED_UNTIL_EXPLICIT_APPROVAL" if not ready else "REQUIRES_EXTERNAL_CERTIFICATION_AND_APPROVAL",
        "safety": dict(SAFETY),
    }


def assert_safe() -> None:
    if SAFETY != {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "automatic_authorization": False,
        "automatic_execution": False,
        "human_decision_required": True,
    }:
        raise AssertionError("ANVIQO safety contract changed")
