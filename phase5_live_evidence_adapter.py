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

    # These are labels from the existing evidence contract, not a new
    # prediction/risk engine. Keep simulator and onboarding evidence explicit.
    tenant_rows = evidence.get("equipment_evidence")
    tenant_evidence = (
        isinstance(tenant_rows, list)
        and str(evidence.get("mode", "")).upper() == "ONBOARDING_DATA"
        and bool(tenant_rows)
    )
    if tenant_evidence:
        situation = "ONBOARDING EVIDENCE"
    elif score is None:
        situation = "NO DATA"
    elif str(evidence.get("mode", "")).upper() == "SIMULATION":
        situation = "DEMO / SIMULATION"
    else:
        situation = "READ-ONLY PLANT EVIDENCE"

    # Tenant evidence metrics are descriptive counts only. They do not infer
    # health, risk, causation, or priority from imported rows.
    evidence_row_count = len(tenant_rows) if isinstance(tenant_rows, list) else 0
    equipment_ids = set()
    tag_ids = set()
    for row in tenant_rows if isinstance(tenant_rows, list) else []:
        if not isinstance(row, dict):
            continue
        for key in ("equipment", "equipment_id", "equipment_tag", "service"):
            value = row.get(key)
            if value not in (None, ""):
                equipment_ids.add(str(value).strip())
                break
        for key in ("tag", "external_id", "instrument_tag"):
            value = row.get(key)
            if value not in (None, ""):
                tag_ids.add(str(value).strip())
                break

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
            "evidence_row_count": evidence_row_count,
            "equipment_identity_count": len(equipment_ids),
            "tag_identity_count": len(tag_ids),
            "evidence_available": bool(evidence.get("evidence_available")),
            "tenant_scope": evidence.get("tenant_scope"),
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
