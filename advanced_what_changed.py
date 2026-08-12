from datetime import datetime


def compare_health(previous, current):
    """
    Compare previous and current health scores.
    """

    try:
        old = float(previous)
        new = float(current)
    except (TypeError, ValueError):
        return {
            "changed": False,
            "message": "Health data unavailable."
        }

    change = round(new - old, 2)

    if change > 0:
        direction = "IMPROVED"
    elif change < 0:
        direction = "DETERIORATED"
    else:
        direction = "UNCHANGED"

    return {
        "changed": change != 0,
        "previous": old,
        "current": new,
        "change": change,
        "direction": direction
    }


def compare_risk(previous, current):
    """
    Compare previous and current risk scores.
    """

    try:
        old = float(previous)
        new = float(current)
    except (TypeError, ValueError):
        return {
            "changed": False,
            "message": "Risk data unavailable."
        }

    change = round(new - old, 2)

    if change > 0:
        direction = "INCREASED"
    elif change < 0:
        direction = "DECREASED"
    else:
        direction = "UNCHANGED"

    return {
        "changed": change != 0,
        "previous": old,
        "current": new,
        "change": change,
        "direction": direction
    }


def identify_significant_parameters(parameters):
    """
    Identify parameters with meaningful changes.
    """

    significant = []

    for item in parameters:

        try:
            percentage = float(
                item.get("percentage_change", 0)
            )
        except (TypeError, ValueError):
            continue

        status = item.get("status", "NORMAL")

        if (
            abs(percentage) >= 10
            or status in (
                "WATCH",
                "EARLY WARNING"
            )
        ):
            significant.append({
                "name": item.get(
                    "name",
                    "Parameter"
                ),
                "percentage_change": percentage,
                "direction": item.get(
                    "direction",
                    "UNKNOWN"
                ),
                "status": status
            })

    return significant


def generate_advanced_what_changed(
    equipment_tag,
    equipment_name,
    previous_health,
    current_health,
    previous_risk,
    current_risk,
    parameters=None,
    events=None,
    area=None
):
    """
    Generate an advanced explanation of what changed.
    """

    parameters = parameters or []
    events = events or []

    health = compare_health(
        previous_health,
        current_health
    )

    risk = compare_risk(
        previous_risk,
        current_risk
    )

    significant = identify_significant_parameters(
        parameters
    )

    findings = []

    # Health finding
    if health.get("change", 0) < 0:

        findings.append(
            f"Equipment health decreased "
            f"from {health['previous']} to "
            f"{health['current']}."
        )

    elif health.get("change", 0) > 0:

        findings.append(
            f"Equipment health improved "
            f"from {health['previous']} to "
            f"{health['current']}."
        )

    # Risk finding
    if risk.get("change", 0) > 0:

        findings.append(
            f"Risk increased from "
            f"{risk['previous']} to "
            f"{risk['current']}."
        )

    elif risk.get("change", 0) < 0:

        findings.append(
            f"Risk decreased from "
            f"{risk['previous']} to "
            f"{risk['current']}."
        )

    # Parameter findings
    for item in significant:

        findings.append(
            f"{item['name']} "
            f"{item['direction'].lower()} "
            f"({item['percentage_change']}%)."
        )

    # Event findings
    for event in events[:5]:

        findings.append(
            f"Event: {event}"
        )

    # Overall significance
    if (
        health.get("change", 0) < 0
        and risk.get("change", 0) > 0
    ):
        significance = (
            "Equipment condition is deteriorating "
            "and requires attention."
        )

    elif significant:

        significance = (
            "Significant parameter changes "
            "require monitoring."
        )

    elif events:

        significance = (
            "Recent equipment events should "
            "be reviewed."
        )

    else:

        significance = (
            "No major change detected."
        )

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment_tag,
        "equipment_name": equipment_name,
        "area": area,
        "health": health,
        "risk": risk,
        "significant_parameters": significant,
        "events": events,
        "findings": findings,
        "significance": significance
    }
