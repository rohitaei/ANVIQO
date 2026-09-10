"""ANVIQO Phase 6 Enterprise Command Centre V4.

Real tenant-scoped plant-context switching. This module changes only the
authenticated session context; it never changes PLC/SCADA state and never
creates intelligence for a plant whose evidence is not actually available.
"""
from __future__ import annotations

from flask import jsonify, request, session

from phase6_enterprise_runtime import app, _actor, _connect, _placeholder, _require_auth, _admin
from anvi_tenant_store import authorize, record_audit

ENTERPRISE_V4_GOVERNANCE = {
    "read_only_intelligence": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def _plant(actor, plant_id):
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT plant_id,organization_id,name,slug,status,created_at FROM anviqo_plants WHERE organization_id={p} AND plant_id={p}",
            (actor["organization_id"], plant_id),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def _can_read_plant(actor, plant_id):
    if _admin(actor):
        return True
    selected_actor = dict(actor)
    selected_actor["plant_id"] = plant_id
    return authorize(selected_actor, "plant:read", actor["organization_id"], plant_id)


@app.route("/api/enterprise/select-plant", methods=["POST"])
def enterprise_select_plant():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    payload = request.get_json(silent=True) or {}
    plant_id = str(payload.get("plant_id", "")).strip()
    if not plant_id:
        return jsonify({"status": "BAD_REQUEST", "message": "plant_id is required", "switched": False, "governance": dict(ENTERPRISE_V4_GOVERNANCE)}), 400

    plant = _plant(actor, plant_id)
    if plant is None:
        return jsonify({"status": "FORBIDDEN", "message": "Plant is outside the active organization", "switched": False, "governance": dict(ENTERPRISE_V4_GOVERNANCE)}), 403
    if not _can_read_plant(actor, plant_id):
        return jsonify({"status": "FORBIDDEN", "message": "plant:read permission is required for the selected plant", "switched": False, "governance": dict(ENTERPRISE_V4_GOVERNANCE)}), 403

    previous_plant_id = actor["plant_id"]
    session["plant_id"] = plant_id
    session.modified = True
    try:
        audit_actor = dict(actor)
        audit_actor["plant_id"] = plant_id
        record_audit(audit_actor, "SELECT_PLANT_CONTEXT", "plant", plant_id, {"previous_plant_id": previous_plant_id})
    except Exception:
        # Context switching remains valid even if optional audit persistence is unavailable.
        pass

    return jsonify({
        "status": "SWITCHED",
        "switched": True,
        "previous_plant_id": previous_plant_id,
        "active_plant_id": plant_id,
        "plant": plant,
        "evidence_scope": {
            "plant_id": plant_id,
            "policy": "existing_evidence_only",
            "status": "CONTEXT_SELECTED",
            "note": "Existing intelligence must be evaluated in this selected plant context; no evidence is fabricated by the context switch.",
        },
        "governance": dict(ENTERPRISE_V4_GOVERNANCE),
    })


@app.route("/api/enterprise/active-context")
def enterprise_active_context():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    plant = _plant(actor, actor["plant_id"]) if actor["plant_id"] else None
    return jsonify({
        "status": "OK",
        "organization_id": actor["organization_id"],
        "active_plant_id": actor["plant_id"],
        "plant": plant,
        "evidence_policy": "existing_evidence_only",
        "governance": dict(ENTERPRISE_V4_GOVERNANCE),
    })
