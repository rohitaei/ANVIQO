"""ANVIQO Maintenance Action Memory V1.

Thin, evidence-gated retrieval over the existing verified Plant Memory.
This module does not create a second memory or reasoning engine.
"""

VERSION = "ANVIQO-MA-MEMORY-V1.0"

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def _text(value):
    return str(value or "").strip()


def _norm_tag(value):
    return _text(value).upper().replace("_", "-").replace(" ", "-")


def _matches(record, tag=None, symptom=None):
    if not isinstance(record, dict):
        return False

    # Maintenance Action Memory is strictly verified-only.
    if record.get("verified") is not True:
        return False

    wanted_tag = _norm_tag(tag)
    wanted_symptom = _text(symptom).lower()
    record_tag = _norm_tag(record.get("tag") or record.get("equipment_tag"))

    if wanted_tag and record_tag != wanted_tag:
        return False

    haystack = " ".join(
        _text(record.get(k))
        for k in (
            "event", "symptom", "finding", "problem", "failure_mode",
            "maintenance_action", "action", "confirmation_evidence",
        )
    ).lower()

    return not wanted_symptom or wanted_symptom in haystack


def retrieve_actions(records, tag=None, symptom=None):
    """Return verified historical maintenance actions matching the request."""
    results = []
    for record in records or []:
        if not _matches(record, tag=tag, symptom=symptom):
            continue

        action = _text(record.get("maintenance_action") or record.get("action"))
        evidence = _text(record.get("confirmation_evidence"))
        if not action or not evidence:
            continue

        results.append({
            "memory_id": _text(record.get("memory_id") or record.get("id")),
            "tag": _text(record.get("tag") or record.get("equipment_tag")),
            "finding": _text(record.get("finding")),
            "maintenance_action": action,
            "confirmation_evidence": evidence,
            "verified": True,
            "source": _text(record.get("source") or "VERIFIED_PLANT_MEMORY"),
        })

    return results


def summarize_actions(records, tag=None, symptom=None):
    matches = retrieve_actions(records, tag=tag, symptom=symptom)
    return {
        "status": "MAINTENANCE_ACTION_MEMORY_AVAILABLE" if matches else "NO_VERIFIED_ACTION_MEMORY",
        "version": VERSION,
        "matches": matches,
        "count": len(matches),
        "safety": SAFETY.copy(),
        "human_decision_required": True,
    }
