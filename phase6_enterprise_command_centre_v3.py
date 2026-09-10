"""ANVIQO Phase 6 Enterprise Command Centre V3.

Portfolio context adapter only. It aggregates tenant plant metadata and,
for the authenticated active plant, reuses the existing live-evidence
contract. It never invents health for plants that have no scoped evidence.
"""
from __future__ import annotations

from flask import jsonify

from phase6_enterprise_runtime import app, _require_auth, _actor, _connect, _placeholder
from phase5_live_evidence_adapter import build_live_management_evidence

ENTERPRISE_V3_GOVERNANCE = {
    "read_only_intelligence": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def _plants(actor):
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT plant_id,name,slug,status,created_at FROM anviqo_plants WHERE organization_id={p} ORDER BY name",
            (actor["organization_id"],),
        )
        return [dict(r) for r in cur.fetchall()]


def _active_evidence(actor):
    """Reuse the existing plant evidence only for the current plant context."""
    try:
        evidence = build_live_management_evidence()
        return {
            "evidence_status": "AVAILABLE",
            "plant_id": actor["plant_id"],
            "mode": evidence.get("evidence_context", {}).get("mode", "READ_ONLY"),
            "plant_health": evidence.get("executive", {}).get("plant_health", {}),
            "management_state": evidence.get("executive", {}).get("management_state"),
        }
    except Exception as exc:
        return {
            "evidence_status": "UNAVAILABLE",
            "plant_id": actor["plant_id"],
            "reason": type(exc).__name__,
        }


@app.route("/api/enterprise/portfolio")
def enterprise_portfolio_api():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    plants = _plants(actor)
    active = _active_evidence(actor) if actor["plant_id"] else {"evidence_status": "NO_ACTIVE_PLANT"}
    for plant in plants:
        if plant["plant_id"] == actor["plant_id"]:
            plant["intelligence_scope"] = "ACTIVE_CONTEXT"
            plant["evidence"] = active
        else:
            plant["intelligence_scope"] = "CONTEXT_ONLY"
            plant["evidence"] = {
                "evidence_status": "NOT_EVALUATED",
                "reason": "Plant is not the authenticated active plant context; no health is fabricated.",
            }
    return jsonify({
        "status": "OK",
        "organization_id": actor["organization_id"],
        "active_plant_id": actor["plant_id"],
        "plant_count": len(plants),
        "evaluated_plant_count": sum(1 for p in plants if p["evidence"]["evidence_status"] == "AVAILABLE"),
        "plants": plants,
        "aggregation_policy": "metadata_all_plants_active_context_evidence_only",
        "governance": dict(ENTERPRISE_V3_GOVERNANCE),
    })
