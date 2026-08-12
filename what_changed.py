def compare_parameters(previous, current):
    """
    Compare previous and current parameter analysis.
    """

    changes = []

    previous_map = {
        item.get("name", "").lower(): item
        for item in previous
    }

    for item in current:

        name = item.get("name", "Parameter")
        key = name.lower()

        old = previous_map.get(key)

        if not old:
            changes.append({
                "parameter": name,
                "type": "NEW_PARAMETER",
                "message": f"{name} is newly being monitored."
            })
            continue

        old_value = old.get("last")
        new_value = item.get("last")

        if old_value is None or new_value is None:
            continue

        try:
            change = float(new_value) - float(old_value)
        except (TypeError, ValueError):
            continue

        if change == 0:
            continue

        direction = "INCREASED" if change > 0 else "DECREASED"

        changes.append({
            "parameter": name,
            "type": "VALUE_CHANGE",
            "direction": direction,
            "previous": old_value,
            "current": new_value,
            "change": round(change, 2),
            "message": (
                f"{name} {direction.lower()} "
                f"from {old_value} to {new_value}."
            )
        })

    return changes


def compare_risk(previous_risk, current_risk):
    """
    Compare previous and current equipment risk.
    """

    try:
        old = float(previous_risk)
        new = float(current_risk)
    except (TypeError, ValueError):
        return {
            "changed": False,
            "message": "Risk data unavailable."
        }

    change = new - old

    if change > 0:
        direction = "INCREASED"
    elif change < 0:
        direction = "DECREASED"
    else:
        direction = "UNCHANGED"

    return {
        "changed": change != 0,
        "direction": direction,
        "previous": old,
        "current": new,
        "change": round(change, 2),
        "message": (
            f"Risk {direction.lower()} "
            f"from {old} to {new}."
        )
    }


def generate_what_changed(
    tag,
    previous_parameters,
    current_parameters,
    previous_risk,
    current_risk
):
    """
    Generate an Anvi-style summary of what changed.
    """

    parameter_changes = compare_parameters(
        previous_parameters,
        current_parameters
    )

    risk_change = compare_risk(
        previous_risk,
        current_risk
    )

    if risk_change.get("change", 0) > 0:
        overall = "Equipment condition is deteriorating."

    elif risk_change.get("change", 0) < 0:
        overall = "Equipment condition is improving."

    elif parameter_changes:
        overall = "Parameter conditions have changed."

    else:
        overall = "No significant change detected."

    return {
        "equipment": tag,
        "risk_change": risk_change,
        "parameter_changes": parameter_changes,
        "overall": overall
    }
