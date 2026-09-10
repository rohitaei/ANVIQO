"""ANVIQO Phase 4 Advanced Plant Intelligence foundation.

Read-only decision-support layer. It consumes evidence supplied by the existing
ANVIQO V5/Phase 2/Phase 3 layers and never writes PLC/SCADA state.

The functions deliberately return INSUFFICIENT_EVIDENCE when required inputs
are absent; they never manufacture plant measurements, production rates,
energy values, safety events, or failure probabilities.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "automatic_authorization": False,
    "causation_claim": False,
}


def _num(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _result(domain: str, status: str, findings: List[Dict[str, Any]], **extra: Any) -> Dict[str, Any]:
    return {"domain": domain, "status": status, "findings": findings, "safety": dict(SAFETY), **extra}


def analyze_energy(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate energy intensity only from explicit energy/output evidence."""
    energy = _num(evidence.get("energy_kwh"))
    output = _num(evidence.get("production_output"))
    if energy is None or output is None or output <= 0:
        return _result("energy", "INSUFFICIENT_EVIDENCE", [], required=["energy_kwh", "production_output"])
    intensity = energy / output
    baseline = _num(evidence.get("baseline_energy_intensity"))
    finding = {"metric": "energy_intensity", "value": intensity, "unit": "kWh/output_unit", "evidence_backed": True}
    if baseline is not None and baseline > 0:
        deviation_pct = ((intensity - baseline) / baseline) * 100.0
        finding.update({"baseline": baseline, "deviation_percent": deviation_pct})
    return _result("energy", "AVAILABLE", [finding])


def analyze_production_impact(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate impact from explicit production exposure, never from invented rates."""
    output = _num(evidence.get("production_output"))
    at_risk = _num(evidence.get("production_at_risk"))
    if at_risk is None and output is None:
        return _result("production_impact", "INSUFFICIENT_EVIDENCE", [], required=["production_output or production_at_risk"])
    findings: List[Dict[str, Any]] = []
    if at_risk is not None:
        findings.append({"metric": "production_at_risk", "value": at_risk, "evidence_backed": True})
    if output is not None and output > 0 and at_risk is not None:
        findings.append({"metric": "at_risk_percent", "value": (at_risk / output) * 100.0, "evidence_backed": True})
    return _result("production_impact", "AVAILABLE", findings)


def analyze_safety(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize explicit safety evidence; does not declare plant safety."""
    events = evidence.get("safety_events")
    if not isinstance(events, list):
        events = []
    if not events and not evidence.get("interlock_status") and not evidence.get("permit_status"):
        return _result("safety", "INSUFFICIENT_EVIDENCE", [], required=["safety_events, interlock_status, or permit_status"])
    findings = []
    for event in events:
        if isinstance(event, dict):
            findings.append({"type": "safety_event", "evidence": event})
        else:
            findings.append({"type": "safety_event", "evidence": str(event)})
    for key in ("interlock_status", "permit_status"):
        if evidence.get(key) is not None:
            findings.append({"type": key, "evidence": evidence[key]})
    return _result("safety", "AVAILABLE", findings, statement="Evidence summary only; qualified human verification required.")


def build_maintenance_plan(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Prioritize explicit risks using existing prediction/root-cause/criticality evidence."""
    candidates = evidence.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return _result("maintenance_planner", "INSUFFICIENT_EVIDENCE", [], required=["candidates"])
    ranked = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        criticality = _num(item.get("criticality")) or 0.0
        risk = _num(item.get("risk_score")) or 0.0
        confidence = _num(item.get("confidence")) or 0.0
        priority = (risk * 0.6) + (criticality * 0.3) + (confidence * 0.1)
        ranked.append({**item, "priority_score": priority, "recommendation_only": True})
    ranked.sort(key=lambda x: x["priority_score"], reverse=True)
    return _result("maintenance_planner", "AVAILABLE" if ranked else "INSUFFICIENT_EVIDENCE", ranked,
                   statement="Recommended work order priority only; no automatic execution.")


def build_reliability_summary(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize explicit verified prediction outcomes and recurring assets."""
    records = evidence.get("prediction_history")
    if not isinstance(records, list) or not records:
        return _result("reliability", "INSUFFICIENT_EVIDENCE", [], required=["prediction_history"])
    verified = [r for r in records if isinstance(r, dict) and r.get("verified") is True]
    failed = [r for r in verified if str(r.get("outcome", "")).upper() in {"FAILURE", "FAILED"}]
    assets: Dict[str, int] = {}
    for row in failed:
        tag = str(row.get("tag", "")).strip()
        if tag:
            assets[tag] = assets.get(tag, 0) + 1
    findings = [{"metric": "verified_predictions", "value": len(verified)},
                {"metric": "verified_failures", "value": len(failed)},
                {"metric": "recurring_verified_failure_assets", "value": assets}]
    return _result("reliability", "AVAILABLE", findings)


def build_phase4_snapshot(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Single read-only Phase 4 aggregation point for future Command Centre wiring."""
    return {
        "phase": "PHASE_4",
        "status": "READY",
        "domains": {
            "energy": analyze_energy(evidence.get("energy", {})),
            "production_impact": analyze_production_impact(evidence.get("production_impact", {})),
            "safety": analyze_safety(evidence.get("safety", {})),
            "maintenance_planner": build_maintenance_plan(evidence.get("maintenance", {})),
            "reliability": build_reliability_summary(evidence.get("reliability", {})),
        },
        "safety": dict(SAFETY),
    }
