"""Phase 5 live-evidence adapter.

Bridges existing ANVIQO evidence into the frozen V5.7 Executive/HOD
contract. This module does not create a new reasoning engine.
"""
from __future__ import annotations


def build_live_management_evidence():
    """Return current read-only evidence from existing ANVIQO services."""
    from anvi_knowledge_layer import _build_unified_plant_evidence_context
    from v57_executive_intelligence import build_executive_intelligence

    evidence = _build_unified_plant_evidence_context()
    score = evidence.get("plant_health_score")
    healthy = evidence.get("healthy", 0)
    warning = evidence.get("warning", 0)
    critical = evidence.get("critical", 0)
    changed = evidence.get("changed", 0)
    events = evidence.get("active_events", 0)

    # These are labels from the existing plant-health contract, not a new
    # prediction/risk engine. Keep the simulator state explicit in the UI.
    if score is None:
        situation = "NO DATA"
    elif str(evidence.get("mode", "")).upper() == "SIMULATION":
        situation = "DEMO / SIMULATION"
    else:
        situation = "READ-ONLY PLANT EVIDENCE"

    changes = []
    if critical:
        changes.append(f"{critical} critical point(s) currently reported")
    if warning:
        changes.append(f"{warning} warning point(s) currently reported")
    if changed:
        changes.append(f"{changed} changed point(s) currently reported")
    if events:
        changes.append(f"{events} active event(s) currently reported")

    executive = build_executive_intelligence(
        plant_status={"status": situation},
        plant_health={"status": situation, "score": score},
        what_changed=changes,
        equipment_risks=[],
        event_chains=[],
        decisions=[],
        shift_summary={
            "healthy": healthy,
            "warning": warning,
            "critical": critical,
            "changed": changed,
            "active_events": events,
            "area_count": evidence.get("area_count"),
            "mode": evidence.get("mode", "READ_ONLY"),
        },
    )

    return {
        "executive": executive,
        "phase4": {},
        "shift": executive.get("shift_summary", {}),
        "areas": evidence.get("areas", []),
        "evidence_context": evidence,
    }
