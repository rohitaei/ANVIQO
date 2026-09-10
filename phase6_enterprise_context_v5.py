"""ANVIQO Phase 6 V5 enterprise context propagation.

This is a transport/context adapter only. It exposes the authenticated
organization + active plant context to downstream Command Centre surfaces
without changing V5 reasoning or inventing plant-scoped evidence.
"""
from __future__ import annotations

from flask import g, jsonify, request, session

from phase6_enterprise_runtime import app, _actor, _require_auth, ENTERPRISE_SAFETY

CONTEXT_CONTRACT = "ANVIQO-PLANT-CONTEXT-V1"
SURFACES = ("chat", "management", "plant_health", "events", "reports")


def _context():
    actor = _actor()
    return {
        "contract": CONTEXT_CONTRACT,
        "organization_id": actor["organization_id"],
        "active_plant_id": actor["plant_id"],
        "role": actor["role"],
        "username": actor["username"],
        "surface": None,
        "evidence_policy": "existing_evidence_only",
        "evidence_binding": "selected_plant_required",
        "governance": dict(ENTERPRISE_SAFETY),
    }


@app.before_request
def _capture_enterprise_context():
    if request.path.startswith("/api/") and session.get("authenticated") and session.get("organization_id"):
        g.anviqo_enterprise_context = _context()


@app.after_request
def _propagate_enterprise_context(response):
    ctx = getattr(g, "anviqo_enterprise_context", None)
    if ctx and request.path.startswith("/api/"):
        response.headers["X-ANVIQO-Context-Contract"] = CONTEXT_CONTRACT
        response.headers["X-ANVIQO-Organization"] = str(ctx["organization_id"])
        response.headers["X-ANVIQO-Active-Plant"] = str(ctx["active_plant_id"] or "")
        response.headers["X-ANVIQO-Evidence-Policy"] = "existing_evidence_only"
    return response


@app.route("/api/enterprise/context-envelope")
def enterprise_context_envelope():
    denied = _require_auth()
    if denied:
        return denied
    surface = str(request.args.get("surface", "")).strip().lower() or None
    if surface not in SURFACES:
        surface = None
    ctx = _context()
    ctx["surface"] = surface
    return jsonify({
        "status": "OK",
        "context": ctx,
        "instruction": "Downstream surfaces must use only evidence demonstrably bound to active_plant_id. If plant binding is unavailable, return NOT_EVALUATED or INSUFFICIENT_EVIDENCE rather than attributing global evidence to the selected plant.",
    })


@app.route("/api/enterprise/context-check", methods=["POST"])
def enterprise_context_check():
    denied = _require_auth()
    if denied:
        return denied
    payload = request.get_json(silent=True) or {}
    plant_id = str(payload.get("plant_id", "")).strip()
    if not plant_id:
        return jsonify({"status": "BAD_REQUEST", "message": "plant_id is required"}), 400
    active = str(session.get("plant_id", ""))
    return jsonify({
        "status": "OK",
        "matches_active_context": plant_id == active,
        "active_plant_id": active,
        "requested_plant_id": plant_id,
        "safe_to_attribute": plant_id == active,
        "evidence_policy": "existing_evidence_only",
        "governance": dict(ENTERPRISE_SAFETY),
    })
