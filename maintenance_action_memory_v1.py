"""ANVIQO Maintenance Action Memory V1.

Read-only retrieval over verified Plant Memory. No PLC/SCADA writes.
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


def _matches(record, tag=None, symptom=None):
    if not isinstance(record, dict):
        return False
    wanted_tag = _text(tag).upper()
    wanted_symptom = _text(symptom).lower()
    record_tag = _text(record.get("tag") or record.get("equipment_tag")).upper()
    haystack = " ".join(
        _text(record.get(k))
        for k in (
            "event", "symptom", "finding", "problem", "failure_mode",
            "maintenance_action", "action", "confirmation_evidence",
        )
    ).lower()
    if wanted_tag and record_tag and wanted_tag != record_tag:
        return False
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
            "verified": bool(record.get("verified", True)),
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
