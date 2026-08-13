from datetime import datetime


def correlate_events(
    equipment_tag,
    events
):
    """
    Correlate chronological equipment events
    into a developing condition.
    """

    if not events:
        return {
            "equipment": equipment_tag,
            "status": "NO DATA",
            "correlation": "No events available.",
            "chain": []
        }

    chain = []

    parameter_events = []
    risk_events = []
    health_events = []

    for event in events:

        event_type = event.get(
            "event_type",
            ""
        )

        if event_type == "PARAMETER_CHANGE":
            parameter_events.append(event)

        elif event_type == "RISK_CHANGE":
            risk_events.append(event)

        elif event_type == "HEALTH_CHANGE":
            health_events.append(event)

    # ---------------------------------
    # Detect parameter relationships
    # ---------------------------------

    air_pressure_drop = False
    valve_position_rise = False
    temperature_rise = False

    for event in parameter_events:

        message = event.get(
            "message",
            ""
        ).lower()

        if (
            "air pressure" in message
            and "decreased" in message
        ):
            air_pressure_drop = True

        if (
            "valve position" in message
            and "increased" in message
        ):
            valve_position_rise = True

        if (
            "temperature" in message
            and "increased" in message
        ):
            temperature_rise = True

    # ---------------------------------
    # Build correlation chain
    # ---------------------------------

    if air_pressure_drop:

        chain.append(
            "Instrument Air Pressure decreased."
        )

    if valve_position_rise:

        chain.append(
            "Valve Position increased."
        )

    if temperature_rise:

        chain.append(
            "Temperature increased."
        )

    if risk_events:

        latest_risk = risk_events[-1]

        chain.append(
            latest_risk.get(
                "message",
                "Risk changed."
            )
        )

    if health_events:

        latest_health = health_events[-1]

        chain.append(
            latest_health.get(
                "message",
                "Health changed."
            )
        )

    # ---------------------------------
    # Determine correlation
    # ---------------------------------

    if (
        air_pressure_drop
        and valve_position_rise
        and temperature_rise
        and risk_events
        and health_events
    ):

        correlation = (
            "The parameter, risk and health events "
            "form a correlated developing condition. "
            "The pattern may indicate control-valve, "
            "positioner or instrument-air deterioration."
        )

        status = "CORRELATED CONDITION"

    elif len(chain) >= 2:

        correlation = (
            "Multiple related events detected. "
            "Further investigation is recommended."
        )

        status = "POSSIBLE CORRELATION"

    else:

        correlation = (
            "Insufficient related events "
            "to establish a correlation."
        )

        status = "INSUFFICIENT EVIDENCE"

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment_tag,
        "status": status,
        "correlation": correlation,
        "chain": chain,
        "event_count": len(events)
    }
