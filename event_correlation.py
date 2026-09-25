"""Universal, evidence-first event correlation for ANVIQO.

This module correlates supplied plant events without assuming PCI tags,
instrument families, process names, or causal relationships.
"""


def _text(value):
    return str(value or "").strip()


def _timestamp(event):
    for key in ("timestamp", "time", "event_time", "created_at"):
        value = _text(event.get(key))
        if value:
            return value
    return ""


def _label(event):
    return (
        _text(event.get("message"))
        or _text(event.get("description"))
        or _text(event.get("event"))
        or _text(event.get("event_type"))
        or "Event"
    )


def _equipment(event):
    for key in ("equipment", "equipment_tag", "tag", "asset", "asset_tag"):
        value = _text(event.get(key))
        if value:
            return value
    return ""


def _event_type(event):
    return _text(event.get("event_type")) or "UNCLASSIFIED"


def correlate_events(equipment_tag, events):
    """Build an evidence chain from arbitrary plant events.

    Correlation means temporal/identity association only. This function does
    not claim physical causation and contains no PCI-specific process rules.
    """
    rows = [e for e in (events or []) if isinstance(e, dict)]
    target = _text(equipment_tag)

    if not rows:
        return {
            "equipment": target,
            "status": "NO DATA",
            "correlation": "No events available.",
            "chain": [],
            "event_count": 0,
            "evidence_basis": [],
            "causation_claimed": False,
        }

    # Preserve source order; when timestamps exist, use them consistently.
    ordered = sorted(
        enumerate(rows),
        key=lambda item: (_timestamp(item[1]) == "", _timestamp(item[1]), item[0]),
    )
    ordered_rows = [item[1] for item in ordered]

    scoped = []
    target_norm = "".join(ch for ch in target.upper() if ch.isalnum())
    for event in ordered_rows:
        event_target = _equipment(event)
        event_norm = "".join(ch for ch in event_target.upper() if ch.isalnum())
        if target_norm and event_norm and event_norm != target_norm:
            continue
        scoped.append(event)

    # If the caller supplied events already scoped to the equipment but the
    # source rows have no equipment identity, retain them.
    if not scoped:
        scoped = ordered_rows

    types = []
    for event in scoped:
        kind = _event_type(event)
        if kind not in types:
            types.append(kind)

    chain = [
        {
            "sequence": index + 1,
            "timestamp": _timestamp(event) or None,
            "event_type": _event_type(event),
            "equipment": _equipment(event) or target or None,
            "message": _label(event),
        }
        for index, event in enumerate(scoped)
    ]

    if len(scoped) >= 2:
        status = "MULTIPLE EVENTS"
        correlation = (
            "Multiple events are associated with the supplied equipment "
            "or event scope. Review the chronological evidence chain; "
            "physical causation is not established."
        )
    else:
        status = "SINGLE EVENT"
        correlation = (
            "One event is available for the supplied equipment or event "
            "scope. There is insufficient event evidence to establish a "
            "relationship."
        )

    return {
        "equipment": target,
        "status": status,
        "correlation": correlation,
        "chain": chain,
        "event_count": len(scoped),
        "event_types": types,
        "evidence_basis": [
            "EVENT_IDENTITY",
            "EVENT_TYPE",
            "EVENT_TIMESTAMP",
            "CHRONOLOGICAL_ASSOCIATION",
        ],
        "causation_claimed": False,
    }
