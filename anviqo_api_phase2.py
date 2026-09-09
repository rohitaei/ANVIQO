"""ANVIQO Phase 2 API boundary.

Wraps the existing V1/V5 API without editing the frozen intelligence modules.
Adds tenant context validation, role/permission enforcement, and tenant audit
for API activity. The underlying V5 plant intelligence remains unchanged.
"""
from flask import jsonify, request, session

from anviqo_api import app
from anvi_tenant_store import authorize, ensure_bootstrap, list_audit, record_audit


def _actor():
    return {
        "user_id": session.get("user_id", ""),
        "organization_id": session.get("organization_id", ""),
        "plant_id": session.get("plant_id", ""),
        "role": session.get("role", ""),
        "username": session.get("username", ""),
    }


def _api_authenticated():
    return request.path.startswith("/api/") and bool(session.get("authenticated"))


@app.before_request
def phase2_tenant_context():
    if not _api_authenticated():
        return None

    actor = _actor()
    if not actor["user_id"] or not actor["organization_id"] or not actor["plant_id"]:
        bootstrap = ensure_bootstrap(session.get("username", ""))
        if not bootstrap:
            return jsonify({"status": "TENANT_UNAVAILABLE", "message": "Tenant context is not configured."}), 503
        session.update(bootstrap)
    return None


@app.before_request
def phase2_authorization():
    if not _api_authenticated():
        return None

    actor = _actor()
    org_id = actor["organization_id"]
    plant_id = actor["plant_id"]

    if not authorize(actor, "tenant:read", org_id, plant_id):
        return jsonify({"status": "FORBIDDEN", "message": "Active tenant membership required."}), 403

    if request.path == "/api/ask" and request.method == "POST":
        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question", ""))
        from pci_spares import _extract_tag
        probe = " " + question.lower() + " "
        mutation_words = (" add ", " added ", " receive ", " received ", " use ", " used ", " remove ", " removed ", " consume ", " consumed ")
        if any(word in probe for word in mutation_words) and _extract_tag(question):
            if not authorize(actor, "inventory:write", org_id, plant_id):
                return jsonify({
                    "status": "FORBIDDEN",
                    "message": "Inventory mutation requires inventory:write permission.",
                    "inventory_mutation": True,
                    "executed": False,
                }), 403
    return None


@app.route("/api/tenant/context")
def tenant_context():
    if not session.get("authenticated"):
        return jsonify({"status": "UNAUTHORIZED", "message": "ANVIQO authentication required"}), 401
    actor = _actor()
    permissions = (
        "tenant:read", "tenant:admin", "audit:read",
        "plant:read", "inventory:read", "inventory:write",
    )
    return jsonify({
        "status": "OK",
        "user": {"user_id": actor["user_id"], "username": actor["username"]},
        "organization_id": actor["organization_id"],
        "plant_id": actor["plant_id"],
        "role": actor["role"],
        "permissions": sorted(p for p in permissions if authorize(actor, p, actor["organization_id"], actor["plant_id"])),
    })


@app.route("/api/tenant/audit")
def tenant_audit():
    if not session.get("authenticated"):
        return jsonify({"status": "UNAUTHORIZED", "message": "ANVIQO authentication required"}), 401
    actor = _actor()
    try:
        limit = max(1, min(int(request.args.get("limit", 100)), 500))
        rows = list_audit(actor, limit)
    except PermissionError as exc:
        return jsonify({"status": "FORBIDDEN", "message": str(exc)}), 403
    return jsonify({
        "status": "OK",
        "organization_id": actor["organization_id"],
        "plant_id": actor["plant_id"],
        "records": rows,
    })


@app.after_request
def phase2_audit_api_activity(response):
    if _api_authenticated() and request.path != "/api/tenant/audit":
        actor = _actor()
        if actor["organization_id"] and actor["plant_id"]:
            try:
                record_audit(
                    actor,
                    "API_ACCESS",
                    "http_endpoint",
                    request.path,
                    {"method": request.method, "status": response.status_code},
                )
            except Exception:
                # Audit must not take down the operational read path.
                pass
    return response
