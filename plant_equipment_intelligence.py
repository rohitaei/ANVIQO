from datetime import datetime

from equipment_database import get_equipment
from equipment_health import get_latest_health
from area_health import build_area_health


def build_area_equipment_intelligence(area):
    """
    Build explainable intelligence from area -> equipment.
    """

    equipment_list = get_equipment()

    area_equipment = [
        item for item in equipment_list
        if str(item.get("area", "")).upper()
        == str(area).upper()
    ]

    contributors = []

    for equipment in area_equipment:

        tag = equipment.get("tag")
        health = get_latest_health(tag)

        if not health:
            continue

        try:
            risk = float(
                health.get("risk_score", 0)
            )
        except (TypeError, ValueError):
            risk = 0

        health_score = max(
            0,
            min(100, 100 - risk)
        )

        contributors.append({
            "tag": tag,
            "name": equipment.get("name", ""),
            "type": equipment.get("type", ""),
            "criticality": equipment.get(
                "criticality",
                "MEDIUM"
            ),
            "risk_score": risk,
            "health_score": health_score,
            "status": health.get(
                "status",
                "UNKNOWN"
            ),
            "priority": health.get(
                "priority",
                "NORMAL"
            ),
            "confidence": health.get(
                "confidence"
            )
        })

    contributors.sort(
        key=lambda item: item["risk_score"],
        reverse=True
    )

    area_result = build_area_health(area)

    if contributors:

        primary = contributors[0]

        explanation = (
            f"{area} area health is "
            f"{area_result.get('status')}. "
            f"Primary contributor is "
            f"{primary['tag']} "
            f"({primary['name']}), "
            f"with risk {primary['risk_score']} "
            f"and health {primary['health_score']}."
        )

    else:

        explanation = (
            f"No equipment health evidence "
            f"is available for {area}."
        )

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "area": area,
        "area_health": area_result,
        "contributors": contributors,
        "primary_contributor": (
            contributors[0]
            if contributors
            else None
        ),
        "explanation": explanation
    }
