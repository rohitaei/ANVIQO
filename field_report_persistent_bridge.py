"""Production bridge for persistent field-report retrieval.

The normal field-report query path uses Plant Memory first. This adapter adds a
small durable fallback to the dedicated Neon field-report table so a report
remains queryable after a Render instance restart even if the local JSON memory
file is empty or incomplete.

This is retrieval only. It does not create new plant reasoning, write PLC/SCADA,
or change inventory.
"""
from __future__ import annotations

import re

from flask import jsonify, request, session

from anviqo_api_phase2 import app


_TAG_RE = re.compile(r"\b([A-Z]{1,8}[-_ ]?\d{1,5})\b", re.I)


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _tokens(value):
    stop = {
        "what", "when", "where", "which", "who", "why", "how", "did",
        "does", "do", "is", "was", "were", "are", "the", "this", "that",
        "last", "time", "about", "tell", "me", "show", "give", "report",
        "reports", "field", "maintenance", "happened", "with", "for", "from",
        "and", "or", "on", "in", "to", "of", "a", "an", "it", "its", "my",
        "our", "plant",
    }
    return {
        x for x in re.findall(r"[a-z0-9]+", _norm(value))
        if len(x) > 2 and x not in stop
    }


def _field_reports_from_neon(tag="", limit=20):
    try:
        from anvi_neon_store import _exec, neon_enabled, init_neon

        if not neon_enabled():
            return []
        init_neon()
        if tag:
            rows = _exec(
                "SELECT payload FROM anviqo_field_reports WHERE tag=%s ORDER BY created_at DESC LIMIT %s",
                (str(tag).strip(), int(limit)),
                True,
            )
        else:
            rows = _exec(
                "SELECT payload FROM anviqo_field_reports ORDER BY created_at DESC LIMIT %s",
                (int(limit),),
                True,
            )
        return [row[0] for row in rows if row and isinstance(row[0], dict)]
    except Exception:
        return []


def _best_report(question, reports, tag=""):
    q_tokens = _tokens(question)
    wanted = _norm(tag)

    def score(report):
        text = _norm(" ".join(
            str(report.get(k, "") or "")
            for k in (
                "event", "observation", "finding", "maintenance_action",
                "outcome", "recovery_status", "spare_used", "notes",
                "tag", "equipment", "area", "source",
            )
        ))
        s = len(q_tokens & _tokens(text)) * 10
        if wanted and wanted == _norm(report.get("tag")):
            s += 100
        if report.get("source") == "technician field report":
            s += 5
        return s

    candidates = [r for r in reports if r.get("source") == "technician field report"]
    if not candidates:
        return None
    return max(candidates, key=score)


@app.before_request
def persistent_field_report_query_bridge():
    """Fallback for /api/ask when local Plant Memory has no report."""
    if not session.get("authenticated") or request.path != "/api/ask" or request.method != "POST":
        return None

    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    if not question:
        return None

    # Let the existing Plant Memory bridge handle normal successful lookups.
    from field_report_runtime import _report_query
    if not _report_query(question):
        return None

    tag_match = _TAG_RE.search(question)
    tag = tag_match.group(1).upper().replace("_", "-").replace(" ", "-") if tag_match else ""
    reports = _field_reports_from_neon(tag=tag, limit=20)
    report = _best_report(question, reports, tag=tag)
    if not report:
        return None

    answer = (
        f"I found a technician field report for {report.get('tag') or report.get('equipment') or 'the equipment'}. "
        f"Observation: {report.get('observation') or 'not stated'}. "
        f"Finding: {report.get('finding') or 'not stated'}. "
        f"Maintenance action: {report.get('maintenance_action') or 'not stated'}. "
        f"Outcome: {report.get('outcome') or 'not stated'}. "
        f"Spare used: {report.get('spare_used') or 'none reported'}."
    )
    if report.get("verification_status") != "VERIFIED":
        answer += " This is a human field report and remains PENDING_VERIFICATION."

    return jsonify({
        "answer": answer,
        "status": "OK",
        "domain": "plant_memory",
        "source": "technician field report",
        "memory_id": report.get("memory_id") or report.get("report_id", ""),
        "verification_status": report.get("verification_status", "PENDING_VERIFICATION"),
        "evidence": report,
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
    })
