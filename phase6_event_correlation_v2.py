"""ANVIQO V2 Command Centre evidence stream.

Universal, tenant-scoped adapter for Event Correlation + What Changed.
It reuses existing live evidence and event-timeline providers. It does not
invent event rows, infer ownership, claim physical causation, or mutate V5.
"""
from __future__ import annotations

from datetime import datetime
from flask import jsonify, request

from phase6_enterprise_runtime import app, _require_auth, _actor
from phase5_live_evidence_adapter import build_live_management_evidence
from event_correlation import correlate_events
from v2_command_centre_stream import build_command_centre_stream

V2_GOVERNANCE = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "human_decision_required": True,
    "causation_claim": False,
}


def _text(value):
    return str(value or "").strip()


def build_what_changed_stream():
    """Build a plant-scoped evidence stream from existing live evidence."""
    evidence = build_live_management_evidence()
    context = evidence.get("evidence_context") or {}
    shift = evidence.get("shift") or {}

    changed = int(context.get("changed") or shift.get("changed") or 0)
    critical = int(context.get("critical") or shift.get("critical") or 0)
    warning = int(context.get("warning") or shift.get("warning") or 0)
    active_events = int(context.get("active_events") or shift.get("active_events") or 0)

    items = []
    if critical:
        items.append({
            "type": "CRITICAL",
            "count": critical,
            "message": f"{critical} critical point(s) currently reported.",
        })
    if warning:
        items.append({
            "type": "WARNING",
            "count": warning,
            "message": f"{warning} warning point(s) currently reported.",
        })
    if changed:
        items.append({
            "type": "CHANGED",
            "count": changed,
            "message": f"{changed} changed point(s) currently reported.",
        })
    if active_events:
        items.append({
            "type": "EVENT",
            "count": active_events,
            "message": f"{active_events} active event(s) currently reported.",
        })

    return {
        "status": "EVIDENCE_AVAILABLE" if items else "NO CHANGE EVIDENCE",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "plant_id": context.get("plant_id"),
        "mode": context.get("mode", "READ_ONLY"),
        "items": items,
        "counts": {
            "critical": critical,
            "warning": warning,
            "changed": changed,
            "active_events": active_events,
        },
        "evidence_source": "EXISTING_LIVE_PLANT_EVIDENCE",
        "evidence_rule": "Only currently available scoped evidence is shown; no synthetic events are created.",
        "governance": dict(V2_GOVERNANCE),
    }


@app.route("/api/command-centre/what-changed")
def command_centre_what_changed():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    if not actor["plant_id"]:
        return jsonify({
            "status": "NO_ACTIVE_PLANT",
            "message": "No active plant context. No global fallback is used.",
            "governance": dict(V2_GOVERNANCE),
        }), 409

    result = build_what_changed_stream()
    result["organization_id"] = actor["organization_id"]
    result["scope"] = "SELECTED_PLANT_ONLY"
    return jsonify(result)


@app.route("/api/command-centre/event-correlation")
def command_centre_event_correlation():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    if not actor["plant_id"]:
        return jsonify({
            "status": "NO_ACTIVE_PLANT",
            "message": "No active plant context. No global fallback is used.",
            "governance": dict(V2_GOVERNANCE),
        }), 409

    equipment = _text(request.args.get("equipment") or request.args.get("tag"))
    if not equipment:
        return jsonify({
            "status": "BAD_REQUEST",
            "message": "equipment (or tag) is required for event correlation.",
            "scope": "SELECTED_PLANT_ONLY",
            "governance": dict(V2_GOVERNANCE),
        }), 400

    try:
        stream = build_command_centre_stream(query=equipment, tag=equipment)
        events = stream.get("events") if isinstance(stream, dict) else []
        events = events if isinstance(events, list) else []
        correlation = stream.get("correlation") if isinstance(stream, dict) else None
        if not isinstance(correlation, dict):
            correlation = correlate_events(equipment, events)
        return jsonify({
            "status": "EVIDENCE_AVAILABLE" if events else "NO EVENT DETAIL",
            "equipment": equipment,
            "plant_id": actor["plant_id"],
            "organization_id": actor["organization_id"],
            "scope": "SELECTED_PLANT_ONLY",
            "timeline_source": "TENANT_SCOPED_COMMAND_CENTRE_STREAM",
            "events": events,
            "changes": stream.get("changes", []) if isinstance(stream, dict) else [],
            "correlation": correlation,
            "evidence_rule": "Only explicit selected-plant event evidence is correlated; physical causation is not established.",
            "governance": dict(V2_GOVERNANCE),
        })
    except Exception as exc:
        return jsonify({
            "status": "ERROR",
            "equipment": equipment,
            "plant_id": actor["plant_id"],
            "scope": "SELECTED_PLANT_ONLY",
            "error": type(exc).__name__,
            "governance": dict(V2_GOVERNANCE),
        }), 500


__all__ = ["build_what_changed_stream", "V2_GOVERNANCE"]
