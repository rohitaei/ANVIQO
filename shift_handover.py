from datetime import datetime


def generate_shift_handover(
    plant_name,
    plant_health,
    plant_trend,
    areas=None,
    equipment=None,
    what_changed=None
):
    """
    Generate a concise Anvi shift-handover report
    from existing intelligence modules.
    """

    areas = areas or []
    equipment = equipment or []
    what_changed = what_changed or []

    health_score = plant_health.get("health_score")
    health_status = plant_health.get("status", "UNKNOWN")

    trend = plant_trend.get("trend", "UNKNOWN")
    trend_status = plant_trend.get("status", "UNKNOWN")

    # ---------------------------------
    # Determine handover priority
    # ---------------------------------

    critical_equipment = [
        item for item in equipment
        if item.get("status") == "CRITICAL"
    ]

    degraded_areas = [
        item for item in areas
        if item.get("status") == "DEGRADED"
    ]

    if critical_equipment:
        priority = "HIGH"

    elif degraded_areas:
        priority = "MEDIUM"

    elif trend_status in ("ATTENTION", "HIGH CONCERN"):
        priority = "MEDIUM"

    else:
        priority = "LOW"

    # ---------------------------------
    # Top concerns
    # ---------------------------------

    concerns = []

    for item in critical_equipment[:5]:

        concerns.append(
            f"{item.get('tag', 'UNKNOWN')} — "
            f"{item.get('health_score', 'N/A')}/100"
        )

    for item in degraded_areas[:5]:

        concerns.append(
            f"{item.get('area', 'UNKNOWN')} — "
            f"{item.get('health_score', 'N/A')}/100"
        )

    # ---------------------------------
    # Build handover
    # ---------------------------------

    report = []

    report.append("ANVI SHIFT HANDOVER")
    report.append("================================")
    report.append("")
    report.append(f"Plant : {plant_name}")
    report.append(
        f"Generated : "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    report.append("")
    report.append("PLANT HEALTH")
    report.append("================================")
    report.append(
        f"Health Score : {health_score}/100"
    )
    report.append(
        f"Status       : {health_status}"
    )
    report.append(
        f"Trend        : {trend}"
    )

    report.append("")
    report.append("SHIFT PRIORITY")
    report.append("================================")
    report.append(priority)

    if concerns:

        report.append("")
        report.append("TOP CONCERNS")
        report.append("================================")

        for index, concern in enumerate(
            concerns,
            start=1
        ):
            report.append(
                f"{index}. {concern}"
            )

    if what_changed:

        report.append("")
        report.append("WHAT CHANGED")
        report.append("================================")

        for change in what_changed[:5]:
            report.append(
                f"• {change}"
            )

    report.append("")
    report.append("NEXT SHIFT FOCUS")
    report.append("================================")

    if critical_equipment:

        for item in critical_equipment[:3]:

            report.append(
                f"→ Investigate "
                f"{item.get('tag', 'equipment')} condition."
            )

    elif degraded_areas:

        for item in degraded_areas[:3]:

            report.append(
                f"→ Monitor "
                f"{item.get('area', 'area')} condition."
            )

    else:

        report.append(
            "→ Continue normal monitoring."
        )

    report.append("")
    report.append("HANDOVER STATUS")
    report.append("================================")
    report.append(
        f"{priority} ATTENTION"
    )

    return "\n".join(report)
