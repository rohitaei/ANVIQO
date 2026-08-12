from datetime import datetime


PRIORITY_ORDER = {
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4,
    "NORMAL": 5
}


def _priority(item):
    status = str(
        item.get("status", "NORMAL")
    ).upper()

    priority = str(
        item.get("priority", "")
    ).upper()

    if status == "CRITICAL":
        return 1

    if priority == "HIGH":
        return 2

    if status in ("DEGRADED", "WATCH"):
        return 3

    return PRIORITY_ORDER.get(
        status,
        5
    )


def build_operational_status(
    plant_name,
    area_results=None,
    equipment_results=None,
    events=None
):
    """
    Build a plant-level operational attention summary.

    Read-only intelligence layer.
    Does not issue control commands.
    """

    area_results = area_results or []
    equipment_results = equipment_results or []
    events = events or []

    critical_areas = []
    attention_areas = []
    critical_equipment = []
    attention_equipment = []

    for area in area_results:

        status = str(
            area.get("status", "NORMAL")
        ).upper()

        if status == "CRITICAL":
            critical_areas.append(area)

        elif status in (
            "DEGRADED",
            "WATCH"
        ):
            attention_areas.append(area)

    for equipment in equipment_results:

        status = str(
            equipment.get("status", "NORMAL")
        ).upper()

        if status == "CRITICAL":
            critical_equipment.append(
                equipment
            )

        elif status in (
            "DEGRADED",
            "WATCH"
        ):
            attention_equipment.append(
                equipment
            )

    priorities = []

    for item in critical_equipment:
        priorities.append({
            "level": "IMMEDIATE ATTENTION",
            "equipment": item.get("tag"),
            "name": item.get("name"),
            "area": item.get("area"),
            "risk_score": item.get("risk_score"),
            "health_score": item.get("health_score"),
            "status": item.get("status"),
            "reason": (
                "Critical equipment condition."
            )
        })

    for item in critical_areas:
        priorities.append({
            "level": "IMMEDIATE ATTENTION",
            "equipment": None,
            "name": None,
            "area": item.get("area"),
            "risk_score": None,
            "health_score": item.get(
                "health_score"
            ),
            "status": item.get("status"),
            "reason": (
                "Critical plant area condition."
            )
        })

    priorities.sort(
        key=_priority
    )

    if critical_equipment or critical_areas:
        overall_status = "CRITICAL"

    elif attention_equipment or attention_areas:
        overall_status = "ATTENTION REQUIRED"

    else:
        overall_status = "NORMAL"

    if critical_equipment:
        summary = (
            f"{len(critical_equipment)} "
            "critical equipment condition(s) "
            "require immediate attention."
        )

    elif critical_areas:
        summary = (
            f"{len(critical_areas)} critical "
            "area(s) require immediate attention."
        )

    elif attention_equipment or attention_areas:
        summary = (
            "Plant conditions require "
            "continued monitoring."
        )

    else:
        summary = (
            "No critical plant condition detected."
        )

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "plant": plant_name,
        "overall_status": overall_status,
        "summary": summary,
        "critical_areas": critical_areas,
        "attention_areas": attention_areas,
        "critical_equipment": critical_equipment,
        "attention_equipment": attention_equipment,
        "priority_list": priorities,
        "recent_events": events[:10],
        "read_only": True
    }
