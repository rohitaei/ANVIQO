from equipment_database import get_equipment
from equipment_health import get_latest_health


def build_area_health(area):
    """
    Build area health automatically from equipment
    assigned to the specified plant area.
    """

    equipment_list = get_equipment()

    area_equipment = [
        item for item in equipment_list
        if str(item.get("area", "")).upper()
        == str(area).upper()
    ]

    if not area_equipment:
        return {
            "area": area,
            "status": "NO DATA",
            "health_score": None,
            "equipment_count": 0,
            "critical_equipment": 0,
            "equipment": []
        }

    health_records = []

    for equipment in area_equipment:

        tag = equipment.get("tag")

        latest = get_latest_health(tag)

        if not latest:
            continue

        try:
            risk = float(latest.get("risk_score", 0))
        except (TypeError, ValueError):
            risk = 0

        health_score = max(0, min(100, 100 - risk))

        health_records.append({
            "tag": tag,
            "name": equipment.get("name", ""),
            "criticality": equipment.get(
                "criticality",
                "MEDIUM"
            ),
            "health_score": health_score,
            "risk_score": risk,
            "status": latest.get(
                "status",
                "UNKNOWN"
            )
        })

    if not health_records:
        return {
            "area": area,
            "status": "NO DATA",
            "health_score": None,
            "equipment_count": 0,
            "critical_equipment": 0,
            "equipment": []
        }

    average_health = round(
        sum(
            item["health_score"]
            for item in health_records
        ) / len(health_records),
        2
    )

    critical_equipment = sum(
        1
        for item in health_records
        if item["status"] == "CRITICAL"
    )

    if average_health < 40:
        status = "CRITICAL"
    elif average_health < 60:
        status = "DEGRADED"
    elif average_health < 80:
        status = "WATCH"
    else:
        status = "HEALTHY"

    return {
        "area": area,
        "health_score": average_health,
        "status": status,
        "equipment_count": len(health_records),
        "critical_equipment": critical_equipment,
        "equipment": health_records
    }
