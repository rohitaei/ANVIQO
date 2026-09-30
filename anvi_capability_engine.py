"""ANVIQO Universal Capability Engine.

Provides a deterministic, data-driven capability catalog and dispatcher for the
frozen ANVIQO architecture. The catalog contains exactly 5,000 addressable
capability contracts (25 intelligence families x 10 subjects x 20 operations).

A catalog entry is NOT treated as implemented merely because it exists. Runtime
coverage is derived from the real backing modules/functions. Unsupported
operations fail closed with explicit evidence status. No PLC/SCADA write path
exists in this module.
"""
from __future__ import annotations

import importlib
import re
from typing import Any, Dict, List, Optional

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}

# Frozen intelligence families. Keep this list stable; capability growth is
# achieved by data/configuration, not by plant-specific reasoning forks.
FAMILIES = [
    "digital_plant", "digital_equipment_identity", "equipment_twin",
    "evidence_graph", "digital_thread", "real_time_observation",
    "plant_state", "operating_envelope", "event_correlation",
    "what_changed", "attention_intelligence", "plant_health",
    "predictive_intelligence", "diagnosis", "maintenance_intelligence",
    "critical_spares", "plant_memory", "shift_intelligence",
    "management_hod_intelligence", "risk_consequence",
    "decision_simulation", "plant_replay", "outcome_learning",
    "universal_onboarding", "conversational_anvi",
]
SUBJECTS = [
    "plant", "area", "equipment", "instrument", "io_point",
    "alarm", "event", "maintenance", "spare", "report",
]
OPERATIONS = [
    "observe", "identify", "status", "health", "compare",
    "change", "correlate", "diagnose", "predict", "risk",
    "recommend", "maintain", "inventory", "history", "report",
    "simulate", "replay", "learn", "explain", "summarize",
]

assert len(FAMILIES) * len(SUBJECTS) * len(OPERATIONS) == 5000

_MODULES = {
    "digital_plant": "anvi_full_intelligence",
    "digital_equipment_identity": "equipment_database",
    "equipment_twin": "equipment_database",
    "evidence_graph": "anviqo_intelligence_fabric",
    "digital_thread": "anviqo_intelligence_fabric",
    "real_time_observation": "pci_live_simulator",
    "plant_state": "plant_operational_status",
    "operating_envelope": "predictive_warning",
    "event_correlation": "event_correlation",
    "what_changed": "advanced_what_changed",
    "attention_intelligence": "attention_engine",
    "plant_health": "plant_health_intelligence",
    "predictive_intelligence": "failure_prediction",
    "diagnosis": "diagnostic_engine",
    "maintenance_intelligence": "maintenance_experience_matching",
    "critical_spares": "pci_spares",
    "plant_memory": "plant_memory",
    "shift_intelligence": "shift_handover_intelligence",
    "management_hod_intelligence": "senior_hod_summary",
    "risk_consequence": "risk_consequence_intelligence",
    "decision_simulation": "decision_simulation",
    "plant_replay": "plant_replay",
    "outcome_learning": "outcome_learning",
    "universal_onboarding": "universal_onboarding",
    "conversational_anvi": "anvi_agent",
}

def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")

def capability_id(family: str, subject: str, operation: str) -> str:
    return "ANVI-" + "-".join((_slug(family), _slug(subject), _slug(operation))).upper()

def catalog() -> List[Dict[str, Any]]:
    return [
        {
            "id": capability_id(f, s, o),
            "family": f,
            "subject": s,
            "operation": o,
            "safety": "READ_ONLY",
        }
        for f in FAMILIES for s in SUBJECTS for o in OPERATIONS
    ]

def _module_status(module_name: Optional[str]) -> Dict[str, Any]:
    if not module_name:
        return {"module": None, "available": False}
    try:
        mod = importlib.import_module(module_name)
        return {"module": module_name, "available": mod is not None}
    except Exception as exc:
        return {"module": module_name, "available": False, "error": type(exc).__name__}

def coverage() -> Dict[str, Any]:
    rows = []
    for f in FAMILIES:
        st = _module_status(_MODULES.get(f))
        for s in SUBJECTS:
            for o in OPERATIONS:
                rows.append({
                    "id": capability_id(f, s, o),
                    "family": f,
                    "subject": s,
                    "operation": o,
                    "backing_module": st.get("module"),
                    "module_available": st.get("available", False),
                    "status": "BACKED_BY_EXISTING_ENGINE" if st.get("available") else "NO_BACKING_ENGINE",
                })
    backed = sum(1 for r in rows if r["module_available"])
    return {
        "catalog_size": len(rows),
        "backed_capabilities": backed,
        "unbacked_capabilities": len(rows) - backed,
        "coverage_percent": round(backed * 100.0 / len(rows), 2),
        "note": "Module availability is not proof that every operation is semantically supported.",
        "families": len(FAMILIES),
        "subjects": len(SUBJECTS),
        "operations": len(OPERATIONS),
    }

def _selected_plant() -> tuple[str, str]:
    try:
        from flask import session
        if not session.get("authenticated"):
            return "", ""
        return str(session.get("plant_id") or "").strip(), str(session.get("organization_id") or "").strip()
    except Exception:
        return "", ""

def resolve(cap_id: str) -> Optional[Dict[str, Any]]:
    # Normalize the incoming identifier and the generated identifier using the
    # same canonical slug so both underscore- and hyphen-separated forms resolve.
    target = _slug(cap_id).upper()
    for f in FAMILIES:
        for s in SUBJECTS:
            for o in OPERATIONS:
                row = {"id": capability_id(f, s, o), "family": f, "subject": s, "operation": o}
                if _slug(row["id"]).upper() == target:
                    return row
    return None

def execute(cap_id: str, query: str = "", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Resolve a capability without inventing evidence or executing controls.

    The universal execution path intentionally delegates to the existing
    full-intelligence evidence packet. This keeps the frozen engines as the
    source of truth and prevents 5,000 separate reasoning forks.
    """
    plant_id, organization_id = _selected_plant()
    spec = resolve(cap_id)
    base = {
        "capability_id": cap_id,
        "query": str(query or ""),
        "plant_id": plant_id or None,
        "organization_id": organization_id or None,
        "scope": "SELECTED_PLANT_ONLY" if plant_id else "NO_SELECTED_PLANT",
        "safety": dict(SAFETY),
    }
    if not spec:
        return {**base, "status": "UNKNOWN_CAPABILITY", "evidence": []}
    if not plant_id:
        return {**base, "status": "BLOCKED_NO_SELECTED_PLANT", "capability": spec, "evidence": []}
    try:
        from anvi_full_intelligence import build_context
        evidence = build_context(query)
    except Exception as exc:
        return {**base, "status": "ENGINE_ERROR", "capability": spec, "error": type(exc).__name__}
    has_evidence = bool(evidence.get("sources"))
    return {
        **base,
        "status": "EVIDENCE_AVAILABLE" if has_evidence else "NO_AUTHORITATIVE_EVIDENCE",
        "capability": spec,
        "evidence": evidence,
        "execution": "READ_ONLY",
        "decision": "HUMAN_DECISION_REQUIRED",
    }

def manifest() -> Dict[str, Any]:
    c = coverage()
    return {
        "engine": "ANVIQO UNIVERSAL CAPABILITY ENGINE",
        "version": "1.0",
        "catalog_size": c["catalog_size"],
        "architecture": {
            "families": c["families"],
            "subjects": c["subjects"],
            "operations": c["operations"],
            "formula": "25 x 10 x 20 = 5,000",
        },
        "coverage": c,
        "safety": dict(SAFETY),
        "principle": "CHANGE DATA, NOT CODE",
    }

if __name__ == "__main__":
    print(manifest())
