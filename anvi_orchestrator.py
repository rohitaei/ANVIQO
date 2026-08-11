from equipment_database import get_equipment
from event_timeline import load_events
from equipment_health import (
    get_latest_health,
    get_health_history,
    calculate_health_trend
)
from reasoning_engine import generate_reasoning
from evidence_reasoning_adapter import (
    build_evidence_reasoning_context
)


def build_reasoning_parameters(events):

    parameters = []

    for event in events:

        if event.get("event_type") != "PARAMETER_CHANGE":
            continue

        data = event.get("data", {})

        name = data.get(
            "parameter",
            "Parameter"
        )

        percentage = data.get(
            "percentage",
            0
        )

        try:
            percentage = float(percentage)
        except (TypeError, ValueError):
            continue

        if percentage >= 20:
            status = "EARLY WARNING"
            direction = "INCREASING"

        elif percentage >= 10:
            status = "WATCH"
            direction = "INCREASING"

        elif percentage <= -20:
            status = "EARLY WARNING"
            direction = "DECREASING"

        elif percentage <= -10:
            status = "WATCH"
            direction = "DECREASING"

        else:
            status = "NORMAL"
            direction = "STABLE"

        parameters.append({
            "name": name,
            "message": event.get(
                "message",
                ""
            ),
            "status": status,
            "direction": direction,
            "percentage_change": percentage
        })

    return parameters


def orchestrate_equipment(equipment_tag):

    result = {
        "equipment": equipment_tag,
        "equipment_data": None,
        "events": [],
        "health": None,
        "health_history": [],
        "health_trend": None,
        "reasoning": None,
        "evidence_context": None
    }

    try:
        result["equipment_data"] = get_equipment(
            equipment_tag
        )
    except Exception as e:
        result["equipment_data"] = {
            "error": str(e)
        }

    try:
        all_events = load_events()

        result["events"] = all_events.get(
            equipment_tag,
            []
        )

    except Exception:
        result["events"] = []

    try:
        result["health"] = get_latest_health(
            equipment_tag
        )

    except Exception as e:
        result["health"] = {
            "error": str(e)
        }

    try:
        result["health_history"] = get_health_history(
            equipment_tag
        )

    except Exception:
        result["health_history"] = []

    try:
        result["health_trend"] = calculate_health_trend(
            equipment_tag
        )

    except Exception as e:
        result["health_trend"] = {
            "error": str(e)
        }

    # -----------------------------------------
    # V4.10 REASONING
    # -----------------------------------------

    try:

        parameters = build_reasoning_parameters(
            result["events"]
        )

        reasoning_context = {
            "parameters": parameters
        }

        result["reasoning"] = generate_reasoning(
            reasoning_context
        )

    except Exception as e:

        result["reasoning"] = {
            "error": str(e)
        }

    # -----------------------------------------
    # V4.11 EVIDENCE CONTEXT
    # -----------------------------------------

    try:

        result["evidence_context"] = (
            build_evidence_reasoning_context(
                equipment_tag
            )
        )

    except Exception as e:

        result["evidence_context"] = {
            "error": str(e)
        }

    return result
