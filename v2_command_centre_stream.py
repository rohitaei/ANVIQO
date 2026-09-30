"""ANVIQO V2 universal Command Centre evidence stream.

Composes explicit tenant event/change evidence into one read-only stream.
It does not infer events from ordinary engineering records and does not
claim physical causation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from event_correlation import correlate_events


SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


_EVENT_KEYS = ("event_type", "event", "message", "description", "event_time", "timestamp")
_CHANGE_KEYS = ("change_type", "previous", "current", "percentage_change", "direction")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("metadata")
    return value if isinstance(value, dict) else {}


def _value(row: dict[str, Any], *keys: str) -> Any:
    meta = _metadata(row)
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
        value = meta.get(key)
        if value not in (None, ""):
            return value
    return None


def _equipment(row: dict[str, Any]) -> str:
    return _text(_value(row, "equipment", "equipment_tag", "asset_tag", "tag", "asset"))


def _is_explicit_event(row: dict[str, Any]) -> bool:
    return any(_value(row, key) not in (None, "") for key in _EVENT_KEYS)


def _is_explicit_change(row: dict[str, Any]) -> bool:
    return any(_value(row, key) not in (None, "") for key in _CHANGE_KEYS)


def _event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": _text(_value(row, "timestamp", "time", "event_time", "created_at")),
        "event_type": _text(_value(row, "event_type")) or "UNCLASSIFIED",
        "equipment": _equipment(row) or None,
        "message": _text(_value(row, "message", "description", "event")) or "Event",
        "source": _text(row.get("source")) or None,
        "external_id": _text(row.get("external_id")) or None,
    }


def _change(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": _text(_value(row, "timestamp", "time", "created_at")) or None,
        "equipment": _equipment(row) or None,
        "parameter": _text(_value(row, "parameter", "name")) or "Parameter",
        "change_type": _text(_value(row, "change_type")) or "VALUE_CHANGE",
        "previous": _value(row, "previous", "previous_value", "old_value"),
        "current": _value(row, "current", "current_value", "new_value"),
        "percentage_change": _value(row, "percentage_change"),
        "direction": _text(_value(row, "direction")) or None,
        "source": _text(row.get("source")) or None,
        "external_id": _text(row.get("external_id")) or None,
    }


def build_command_centre_stream(query: str = "", tag: str | None = None) -> dict[str, Any]:
    """Build the selected-plant event/change stream from explicit evidence only."""
    try:
        from flask import has_request_context, session
        authenticated = bool(has_request_context() and session.get("authenticated"))
        plant_id = _text(session.get("plant_id")) if authenticated else ""
        organization_id = _text(session.get("organization_id")) if authenticated else ""
    except Exception:
        authenticated = False
        plant_id = ""
        organization_id = ""

    if not authenticated or not plant_id:
        return {
            "status": "NO TENANT CONTEXT",
            "scope": "NONE",
            "events": [],
            "changes": [],
            "correlation": None,
            "evidence_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "safety": dict(SAFETY),
            "decision_status": "HUMAN_DECISION_REQUIRED",
        }

    try:
        from anvi_tenant_chat_boundary import _rows
        rows = _rows(plant_id, tag=tag, limit=2500) if tag else _rows(plant_id, limit=2500)
    except Exception:
        rows = []

    rows = [
        row for row in rows
        if isinstance(row, dict) and _text(row.get("plant_id")) == plant_id
    ]

    try:
        from v2_simulation_state import get as get_simulation_evidence
        rows.extend(get_simulation_evidence(plant_id, tag=tag))
    except Exception:
        pass

    events = [_event(row) for row in rows if _is_explicit_event(row)]
    changes = [_change(row) for row in rows if _is_explicit_change(row)]

    if tag:
        normalized = "".join(ch for ch in _text(tag).upper() if ch.isalnum())
        events = [
            row for row in events
            if not row["equipment"]
            or "".join(ch for ch in row["equipment"].upper() if ch.isalnum()) == normalized
        ]
        changes = [
            row for row in changes
            if not row["equipment"]
            or "".join(ch for ch in row["equipment"].upper() if ch.isalnum()) == normalized
        ]

    correlation = correlate_events(tag or "", events) if events else {
        "equipment": tag or "",
        "status": "NO DATA",
        "correlation": "No explicit event evidence is available.",
        "chain": [],
        "event_count": 0,
        "evidence_basis": [],
        "causation_claimed": False,
    }

    if changes:
        change_status = "CHANGES AVAILABLE"
    else:
        change_status = "NO CHANGE BASELINE"

    return {
        "version": "ANVIQO-V2-COMMAND-CENTRE-STREAM",
        "status": "OK" if (events or changes) else "NO DATA",
        "change_status": change_status,
        "scope": "SELECTED_PLANT_ONLY",
        "plant_id": plant_id,
        "organization_id": organization_id or None,
        "query": query,
        "tag": tag,
        "events": events,
        "changes": changes,
        "correlation": correlation,
        "evidence_count": len(events) + len(changes),
        "causation_claimed": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "safety": dict(SAFETY),
        "decision_status": "HUMAN_DECISION_REQUIRED",
    }
