"""ANVIQO Master Capability Audit.

Read-only audit of the frozen product architecture. It distinguishes:
1) catalog contract,
2) backing implementation present,
3) runtime evidence/acceptance,
4) external plant gate.

It never executes plant controls and never marks an external gate complete.
"""
from __future__ import annotations
import importlib
from typing import Any, Dict

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_execution": False,
    "human_decision_required": True,
}

BACKING = {
    "digital_plant": "anvi_full_intelligence",
    "digital_equipment_identity": "digital_equipment_identity",
    "equipment_twin": "digital_equipment_twin",
    "evidence_graph": "anviqo_intelligence_fabric",
    "digital_thread": "anviqo_intelligence_fabric",
    "real_time_observation": "pci_live_simulator",
    "plant_state": "plant_operational_status",
    "operating_envelope": "predictive_warning",
    "event_correlation": "event_correlation",
    "what_changed": "advanced_what_changed",
    "attention_intelligence": "maintenance_priority_engine",
    "plant_health": "plant_health_intelligence",
    "predictive_intelligence": "failure_prediction",
    "diagnosis": "diagnostic_engine",
    "maintenance_intelligence": "maintenance_experience_matching",
    "critical_spares": "pci_spares",
    "plant_memory": "plant_memory",
    "shift_intelligence": "shift_handover_intelligence",
    "management_hod_intelligence": "senior_hod_summary",
    "risk_consequence": "phase4_advanced_intelligence",
    "decision_simulation": None,
    "plant_replay": None,
    "outcome_learning": "maintenance_learning",
    "universal_onboarding": "universal_onboarding",
    "conversational_anvi": "anvi_agent",
    "voice_anvi": "anvi_voice",
    "tenant_isolation": "anvi_tenant_chat_boundary",
    "human_governance": "phase5_human_management_intelligence",
}

EXTERNAL_GATES = {
    "real_time_observation": "Approved read-only PLC/protocol/network connection",
    "universal_onboarding": "Full MBF-2 import and ANVI acceptance on live deployment",
    "decision_simulation": "Frozen architecture contract exists; no standalone production backing module identified",
    "plant_replay": "Frozen architecture contract exists; no standalone production backing module identified",
    "outcome_learning": "Requires verified outcome records from actual operation",
}

def _importable(name: str | None) -> bool:
    if not name:
        return False
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False

def audit() -> Dict[str, Any]:
    rows = []
    for family, module in BACKING.items():
        available = _importable(module)
        gate = EXTERNAL_GATES.get(family)
        rows.append({
            "family": family,
            "backing_module": module,
            "module_available": available,
            "external_gate": gate,
            "status": (
                "EXTERNAL_ACCEPTANCE_PENDING" if gate else
                "BACKING_MODULE_PRESENT" if available else
                "BACKING_MODULE_MISSING"
            ),
        })
    present = sum(r["module_available"] for r in rows)
    pending = sum(1 for r in rows if r["status"] == "EXTERNAL_ACCEPTANCE_PENDING")
    missing = sum(1 for r in rows if r["status"] == "BACKING_MODULE_MISSING")
    return {
        "product": "ANVIQO",
        "audit": "MASTER_FROZEN_ARCHITECTURE",
        "families": len(rows),
        "backing_modules_present": present,
        "external_acceptance_pending": pending,
        "backing_modules_missing": missing,
        "rows": rows,
        "safety": dict(SAFETY),
        "rule": "Module presence is not proof of production completeness.",
    }

if __name__ == "__main__":
    import json
    print(json.dumps(audit(), indent=2, default=str))
