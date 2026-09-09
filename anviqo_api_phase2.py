"""ANVIQO Phase 2 API boundary.

Wraps the existing V1/V5 API without editing the frozen intelligence modules.
Adds tenant context validation, role/permission enforcement, tenant audit,
and the field-report runtime bridge. The underlying V5 plant intelligence
remains unchanged.
"""
from flask import jsonify, request, session
import json

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


@app.before_request
def phase2_field_report_query_bridge():
    """Answer report-history questions from persistent Plant Memory first.

    This is an integration-layer bridge, not a replacement for V5 reasoning.
    It fixes the case where a captured report exists but the normal knowledge
    router does not return the stored human evidence on a later question.
    """
    if not _api_authenticated():
        return None
    if request.path != "/api/ask" or request.method != "POST":
        return None

    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    if not question:
        return None

    try:
        from field_report_runtime import answer_field_report_query
        answer = answer_field_report_query(question)
        if answer:
            return jsonify(answer)
    except Exception:
        pass
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
def phase2_field_report_spare_sync(response):
    """Apply explicit spare usage captured by a field report exactly once."""
    if not _api_authenticated() or request.path != "/api/field_report" or request.method != "POST":
        return response
    if response.status_code >= 400:
        return response

    try:
        payload = response.get_json(silent=True) or {}
        parsed = payload.get("parsed_report") or {}
        memory = payload.get("memory") or {}
        report_id = str(memory.get("memory_id", "")).strip()
        if report_id and parsed:
            from field_report_runtime import sync_field_report_spare
            inventory_update = sync_field_report_spare(parsed, report_id)
            payload["inventory_update"] = inventory_update
            payload["message"] = (
                "Field report captured and stored in Plant Memory. "
                + inventory_update.get("message", "")
            ).strip()
            response.set_data(json.dumps(payload))
            response.content_type = "application/json"
    except Exception as exc:
        try:
            payload = response.get_json(silent=True) or {}
            payload["inventory_update"] = {
                "status": "ERROR",
                "inventory_changed": False,
                "message": str(exc),
            }
            response.set_data(json.dumps(payload))
            response.content_type = "application/json"
        except Exception:
            pass
    return response


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
                pass
    return response
