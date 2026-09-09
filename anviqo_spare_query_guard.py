"""ANVIQO production entrypoint with safe spare intent and repair command guard."""
from __future__ import annotations
import re
from flask import jsonify, request, session


def _is_read_question(question: str) -> bool:
    q = str(question or "").strip().lower()
    if not q:
        return False
    if "?" in q:
        return True
    return q.startswith(("what ", "which ", "where ", "when ", "why ", "how ", "is ", "are ", "was ", "were ", "did ", "do ", "does ", "can ", "could ", "would ", "will ", "show ", "tell me ", "give me ", "find ", "list "))


def _is_reconcile_command(question: str) -> bool:
    q = re.sub(r"[^a-z0-9-]+", " ", str(question or "").strip().lower())
    return "reconcile" in q and "spare" in q and ("field report" in q or "report" in q)


def _extract_tag(question: str) -> str:
    m = re.search(r"\b([a-z]{1,8}[- ]?\d{1,5})\b", str(question or ""), re.I)
    return m.group(1).upper().replace(" ", "-") if m else ""

import pci_spares

_original_v18_action = getattr(pci_spares, "_v18_action", None)
if callable(_original_v18_action):
    def _guarded_v18_action(question, _original=_original_v18_action):
        if _is_read_question(question) or _is_reconcile_command(question):
            return None
        return _original(question)
    pci_spares._v18_action = _guarded_v18_action

from anviqo_api_phase2 import app  # noqa: E402
import failure_prediction_api  # noqa: E402,F401


@app.before_request
def _reconcile_command_bridge():
    """Route a conversational reconcile command to the authorized repair path."""
    if request.path != "/api/ask" or request.method != "POST" or not session.get("authenticated"):
        return None
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    if not _is_reconcile_command(question):
        return None

    actor = {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}
    from anvi_tenant_store import authorize
    if not authorize(actor, "inventory:write", actor["organization_id"], actor["plant_id"]):
        return jsonify({"status": "FORBIDDEN", "domain": "critical_spares", "message": "Spare reconciliation requires inventory:write permission.", "inventory_changed": False, "plc_write": False, "scada_control": False}), 403

    try:
        from field_report_spare_reconcile import reconcile_field_report_spares
        tag = _extract_tag(question)
        result = reconcile_field_report_spares(tag=tag)
        return jsonify({
            "status": result.get("status", "OK"),
            "domain": "critical_spares",
            "answer": f"Historical field-report spare reconciliation completed for {tag or 'all eligible tags'}. Applied: {result.get('applied_count', 0)}; already applied: {result.get('already_applied_count', 0)}; errors: {result.get('error_count', 0)}.",
            "inventory_update": result,
            "inventory_changed": bool(result.get("applied_count")),
            "read_only": False,
            "plc_write": False,
            "scada_control": False,
            "human_decision_required": True,
        })
    except Exception as exc:
        return jsonify({"status": "ERROR", "domain": "critical_spares", "message": str(exc), "inventory_changed": False, "plc_write": False, "scada_control": False, "human_decision_required": True}), 500