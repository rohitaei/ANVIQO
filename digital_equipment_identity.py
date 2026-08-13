from equipment_database import get_equipment
from equipment_health import (
    get_latest_health,
    calculate_health_trend
)
from event_timeline import load_events
from evidence_reasoning_adapter import (
    build_evidence_reasoning_context
)


def _clean_evidence(raw):
    """
    Normalize the V4.11 evidence adapter output
    into one clean V5 Digital Identity structure.
    """

    if not isinstance(raw, dict):
        return {
            "available": False,
            "strong": False,
            "verified_actions": 0,
            "improvement_rate": 0.0,
            "strength": "INSUFFICIENT DATA",
            "status": "NO EVIDENCE"
        }

    # V4.11 adapter currently stores aggregation
    # inside raw["evidence"]. Support both structures.
    data = raw.get("evidence", raw)

    if not isinstance(data, dict):
        data = {}

    return {
        "available": bool(
            raw.get(
                "evidence_available",
                data.get("verified_actions", 0) > 0
            )
        ),
        "strong": bool(
            raw.get(
                "evidence_strong",
                data.get("evidence_strength") == "STRONG"
            )
        ),
        "verified_actions": data.get(
            "verified_actions",
            raw.get("verified_actions", 0)
        ),
        "improvement_rate": data.get(
            "improvement_rate",
            raw.get("improvement_rate", 0.0)
        ),
        "strength": data.get(
            "evidence_strength",
            "INSUFFICIENT DATA"
        ),
        "status": data.get(
            "status",
            "NO EVIDENCE"
        )
    }


def build_digital_identity(equipment_tag):
    """
    ANVIQO V5.0
    Digital Equipment Identity.

    Reads the existing V4.11 intelligence system and
    presents it through one clean equipment identity.
    """

    equipment = get_equipment(equipment_tag)

    if not equipment:
        return {
            "equipment": equipment_tag,
            "status": "NOT FOUND"
        }

    try:
        health = get_latest_health(equipment_tag)
    except Exception as e:
        health = {
            "error": str(e)
        }

    try:
        health_trend = calculate_health_trend(
            equipment_tag
        )
    except Exception as e:
        health_trend = {
            "error": str(e)
        }

    try:
        all_events = load_events()
        events = all_events.get(
            equipment_tag,
            []
        )
    except Exception:
        events = []

    try:
        raw_evidence = build_evidence_reasoning_context(
            equipment_tag
        )
        evidence = _clean_evidence(
            raw_evidence
        )
    except Exception as e:
        evidence = {
            "available": False,
            "strong": False,
            "verified_actions": 0,
            "improvement_rate": 0.0,
            "strength": "ERROR",
            "status": str(e)
        }

    return {
        "status": "ACTIVE",

        "identity": {
            "tag": equipment.get("tag"),
            "name": equipment.get("name"),
            "type": equipment.get("type"),
            "criticality": equipment.get("criticality")
        },

        "plant": {
            "area": equipment.get("area"),
            "location": equipment.get("location"),
            "service": equipment.get("service")
        },

        "automation": {
            "plc": equipment.get("plc"),
            "io_address": equipment.get("io_address"),
            "jb": equipment.get("jb"),
            "terminal": equipment.get("terminal")
        },

        "technical": {
            "range": equipment.get("range"),
            "unit": equipment.get("unit"),
            "manufacturer": equipment.get("manufacturer"),
            "model": equipment.get("model"),
            "serial_number": equipment.get("serial_number")
        },

        "lifecycle": {
            "installation_date":
                equipment.get("installation_date"),
            "expected_life":
                equipment.get("expected_life"),
            "expiry_date":
                equipment.get("expiry_date")
        },

        "spares": {
            "available":
                equipment.get("spare_available"),
            "quantity":
                equipment.get("spare_quantity"),
            "location":
                equipment.get("spare_location")
        },

        "intelligence": {
            "health": health,
            "health_trend": health_trend,
            "event_count": len(events),
            "evidence": evidence
        }
    }
