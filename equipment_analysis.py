from equipment_database import get_equipment


def attach_equipment_to_analysis(tag, reasoning_result):
    """
    Connect an Anvi risk/analysis result to a registered equipment asset.
    """

    equipment = get_equipment(tag)

    if not equipment:
        return {
            "success": False,
            "message": f"Equipment {tag} not found.",
            "equipment": None,
            "analysis": reasoning_result
        }

    risk_score = reasoning_result.get("risk_score", 0)
    priority = reasoning_result.get("priority", "UNKNOWN")
    confidence = reasoning_result.get("confidence", 0)

    if risk_score >= 80:
        health_status = "CRITICAL"
    elif risk_score >= 60:
        health_status = "DEGRADED"
    elif risk_score >= 40:
        health_status = "WATCH"
    else:
        health_status = "HEALTHY"

    return {
        "success": True,

        "equipment": {
            "tag": equipment.get("tag"),
            "name": equipment.get("name"),
            "type": equipment.get("type"),
            "area": equipment.get("area"),
            "location": equipment.get("location"),
            "service": equipment.get("service"),
            "criticality": equipment.get("criticality"),

            "plc": equipment.get("plc"),
            "io_address": equipment.get("io_address"),
            "jb": equipment.get("jb"),
            "terminal": equipment.get("terminal"),

            "spare_available": equipment.get("spare_available"),
            "spare_quantity": equipment.get("spare_quantity"),
            "spare_location": equipment.get("spare_location"),

            "expiry_date": equipment.get("expiry_date")
        },

        "health": {
            "status": health_status,
            "priority": priority,
            "risk_score": risk_score,
            "confidence": confidence
        },

        "analysis": reasoning_result
    }
