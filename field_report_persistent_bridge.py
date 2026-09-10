"""Production bridge for persistent field-report retrieval.

The normal field-report query path uses Plant Memory first. This adapter adds a
small durable fallback to the dedicated Neon field-report table so a report
remains queryable after a Render instance restart even if the local JSON memory
file is empty or incomplete.

This is retrieval only. It does not create new plant reasoning, write PLC/SCADA,
or change inventory. Tenant filtering is mandatory for the durable fallback.
"""
from __future__ import annotations

import re

from flask import jsonify, request, session

from anviqo_api_phase2 import app


_TAG_RE = re.compile(r"\b([A-Z]{1,8}[-_ ]?\d{1,5})\b", re.I)


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _tag_norm(value):
    return re.sub(r"[^a-z0-9]", "", _norm(value))


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
        org_id = str(session.get("organization_id", "")).strip()
        plant_id = str(session.get("plant_id", "")).strip()
        if not org_id or not plant_id:
            return []

        # Field-report payloads are tenant-scoped. Legacy reports without
        # tenant metadata are intentionally excluded from this fallback.
        if tag:
            rows = _exec(
                """SELECT payload FROM anviqo_field_reports
                   WHERE payload->>'organization_id'=%s
                     AND payload->>'plant_id'=%s
                     AND regexp_replace(lower(COALESCE(tag,'')), '[^a-z0-9]', '', 'g') = regexp_replace(lower(%s), '[^a-z0-9]', '', 'g')
                   ORDER BY created_at DESC LIMIT %s""",
                (org_id, plant_id, str(tag).strip(), int(limit)),
                True,
            )
        else:
            rows = _exec(
                """SELECT payload FROM anviqo_field_reports
                   WHERE payload->>'organization_id'=%s
                     AND payload->>'plant_id'=%s
                   ORDER BY created_at DESC LIMIT %s""",
                (org_id, plant_id, int(limit)),
                True,
            )
        return [row[0] for row in rows if row and isinstance(row[0], dict)]
    except Exception:
        return []


def _report_view(report):
    """Flatten the stored report payload without changing stored data."""
    if not isinstance(report, dict):
        return {}
    parsed = report.get("parsed_report")
    if isinstance(parsed, dict):
        merged = dict(report)
        for key, value in parsed.items():
            if value not in (None, ""):
                merged[key] = value
        return merged
    return report


def _best_report(question, reports, tag=""):
    q_tokens = _tokens(question)
    wanted = _tag_norm(tag)

    def score(report):
        view = _report_view(report)
        text = _norm(" ".join(
            str(view.get(k, "") or "")
            for k in (
                "event", "observation", "finding", "maintenance_action",
                "outcome", "recovery_status", "spare_used", "notes",
                "tag", "equipment", "area", "source",
            )
        ))
        s = len(q_tokens & _tokens(text)) * 10
        if wanted and wanted == _tag_norm(view.get("tag")):
            s += 100
        if view.get("source") == "technician field report":
            s += 5
        return s

    candidates = [r for r in reports if _report_view(r).get("source") == "technician field report"]
    if not candidates:
        return None
    return max(candidates, key=score)


@app.before_request
def persistent_field_report_query_bridge():
    """Fallback for /api/ask when local Plant Memory has no report."""
    # Phase 2 establishes authenticated tenant context using user_id. Keep
    # this bridge aligned with that boundary; do not invent a second auth flag.
    if not session.get("user_id") or request.path != "/api/ask" or request.method != "POST":
        return None

    payload = request.get_json(silent=True) or {}
    question = str(
        payload.get("question")
        or payload.get("query")
        or payload.get("message")
        or payload.get("text")
        or ""
    ).strip()
    if not question:
        return None

    from field_report_runtime import _report_query
    if not _report_query(question):
        return None

    tag_match = _TAG_RE.search(question)
    tag = tag_match.group(1).upper().replace("_", "-").replace(" ", "-") if tag_match else ""
    reports = _field_reports_from_neon(tag=tag, limit=20)
    report = _best_report(question, reports, tag=tag)
    if not report:
        return None

    view = _report_view(report)
    answer = (
        f"I found a technician field report for {view.get('tag') or view.get('equipment') or 'the equipment'}. "
        f"Observation: {view.get('observation') or 'not stated'}. "
        f"Finding: {view.get('finding') or 'not stated'}. "
        f"Maintenance action: {view.get('maintenance_action') or 'not stated'}. "
        f"Outcome: {view.get('outcome') or 'not stated'}. "
        f"Spare used: {view.get('spare_used') or 'none reported'}."
    )
    if view.get("verification_status") != "VERIFIED":
        answer += " This is a human field report and remains PENDING_VERIFICATION."

    return jsonify({
        "answer": answer,
        "status": "OK",
        "domain": "plant_memory",
        "source": "technician field report",
        "memory_id": view.get("memory_id") or view.get("report_id", ""),
        "verification_status": view.get("verification_status", "PENDING_VERIFICATION"),
        "evidence": report,
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
    })
