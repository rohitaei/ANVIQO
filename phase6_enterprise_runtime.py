"""ANVIQO Phase 6 enterprise control-plane adapter.

Adds organization/plant visibility and plant administration on top of the
existing Command Centre runtime and Phase 2 tenant store. Frozen V5
intelligence is not modified. This is governance/context only.
"""
from __future__ import annotations

from flask import jsonify, request, session

from phase5_command_centre_runtime import app
from anvi_tenant_store import authorize, create_plant, _connect, _placeholder

ENTERPRISE_SAFETY = {
    "read_only_intelligence": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def _actor():
    return {
        "user_id": session.get("user_id", ""),
        "organization_id": session.get("organization_id", ""),
        "plant_id": session.get("plant_id", ""),
        "role": session.get("role", ""),
        "username": session.get("username", ""),
    }


def _admin(actor):
    """Tenant admin is organization-scoped, not tied to the selected plant."""
    if not actor["organization_id"] or not actor["user_id"]:
        return False
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT 1 FROM anviqo_memberships m JOIN anviqo_roles r ON r.role_id=m.role_id WHERE m.user_id={p} AND m.organization_id={p} AND m.status='ACTIVE' AND r.name IN ('OWNER','ADMIN') LIMIT 1",
            (actor["user_id"], actor["organization_id"]),
        )
        return cur.fetchone() is not None


def _require_auth():
    if not session.get("authenticated"):
        return jsonify({"status": "UNAUTHORIZED", "message": "ANVIQO authentication required"}), 401
    actor = _actor()
    if not actor["organization_id"]:
        return jsonify({"status": "TENANT_UNAVAILABLE", "message": "Active organization context is required"}), 503
    return None


@app.route("/api/enterprise/context")
def enterprise_context():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT organization_id,name,slug,status,created_at FROM anviqo_organizations WHERE organization_id={p}", (actor["organization_id"],))
        org = cur.fetchone()
        cur.execute(f"SELECT plant_id,name,slug,status,created_at FROM anviqo_plants WHERE organization_id={p} ORDER BY name", (actor["organization_id"],))
        plants = [dict(r) for r in cur.fetchall()]
    return jsonify({"status": "OK", "organization": dict(org) if org else None, "active_plant_id": actor["plant_id"], "role": actor["role"], "plants": plants, "governance": dict(ENTERPRISE_SAFETY)})


@app.route("/api/enterprise/plants", methods=["POST"])
def enterprise_create_plant():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    if not _admin(actor):
        return jsonify({"status": "FORBIDDEN", "message": "tenant:admin permission is required", "created": False, "governance": dict(ENTERPRISE_SAFETY)}), 403
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    slug = str(payload.get("slug", "")).strip().lower()
    if not name or not slug:
        return jsonify({"status": "BAD_REQUEST", "message": "name and slug are required", "created": False}), 400
    try:
        plant_id = create_plant(actor["organization_id"], name, slug)
        return jsonify({"status": "CREATED", "plant_id": plant_id, "organization_id": actor["organization_id"], "created": True, "governance": dict(ENTERPRISE_SAFETY)}), 201
    except Exception as exc:
        return jsonify({"status": "ERROR", "message": str(exc), "created": False, "governance": dict(ENTERPRISE_SAFETY)}), 400


@app.route("/api/enterprise/plant/<plant_id>")
def enterprise_plant(plant_id: str):
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT plant_id,organization_id,name,slug,status,created_at FROM anviqo_plants WHERE organization_id={p} AND plant_id={p}", (actor["organization_id"], plant_id))
        row = cur.fetchone()
    if row is None:
        return jsonify({"status": "FORBIDDEN", "message": "Plant is outside the active organization", "governance": dict(ENTERPRISE_SAFETY)}), 403
    if not _admin(actor) and not authorize(actor, "plant:read", actor["organization_id"], plant_id):
        return jsonify({"status": "FORBIDDEN", "message": "plant:read permission is required for this plant", "governance": dict(ENTERPRISE_SAFETY)}), 403
    return jsonify({"status": "OK", "plant": dict(row), "governance": dict(ENTERPRISE_SAFETY)})


import phase6_enterprise_command_centre_v2  # noqa: E402,F401
import phase6_enterprise_command_centre_v3  # noqa: E402,F401
