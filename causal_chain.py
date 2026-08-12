from datetime import datetime


def build_causal_chain(
    equipment_tag,
    equipment_name,
    correlated_events,
    assessment=None,
    verification_checks=None
):
    """
    Convert correlated events into:
    FACTS -> RELATIONSHIP -> POSSIBLE CAUSE -> VERIFICATION

    The cause is deliberately labelled as POSSIBLE.
    """

    correlated_events = correlated_events or []
    verification_checks = verification_checks or []

    facts = []

    for event in correlated_events:
        message = event.get("message")

        if message:
            facts.append(message)

    # Detect known CV / positioner pattern.
    text = " ".join(facts).lower()

    air_drop = (
        "air pressure" in text
        and "decreased" in text
    )

    valve_rise = (
        "valve position" in text
        and "increased" in text
    )

    temperature_rise = (
        "temperature" in text
        and "increased" in text
    )

    risk_increase = (
        "risk increased" in text
    )

    health_decrease = (
        "health decreased" in text
    )

    relationships = []

    if air_drop and valve_rise:
        relationships.append(
            "Instrument air pressure decreased "
            "while valve position increased."
        )

    if valve_rise and temperature_rise:
        relationships.append(
            "Valve position increased while "
            "temperature also increased."
        )

    if risk_increase and health_decrease:
        relationships.append(
            "Risk increased while equipment health "
            "decreased."
        )

    # Possible cause — never state as confirmed.
    possible_causes = []

    if air_drop and valve_rise:
        possible_causes.append(
            "Possible instrument-air, positioner "
            "or I/P converter deterioration."
        )

    if valve_rise and temperature_rise:
        possible_causes.append(
            "Possible control-valve response "
            "or process-control degradation."
        )

    if not possible_causes:
        possible_causes.append(
            "No specific cause can be inferred "
            "from the available evidence."
        )

    # Default verification checks.
    if not verification_checks and air_drop:
        verification_checks = [
            "Verify instrument-air pressure "
            "directly at the positioner.",
            "Check air regulator, tubing and "
            "possible leaks.",
            "Compare valve command with actual "
            "position feedback.",
            "Inspect positioner and I/P converter "
            "diagnostics."
        ]

    if (
        air_drop
        and valve_rise
        and temperature_rise
        and risk_increase
        and health_decrease
    ):
        confidence = "HIGH"
    elif len(relationships) >= 1:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment_tag,
        "equipment_name": equipment_name,
        "facts": facts,
        "relationships": relationships,
        "possible_causes": possible_causes,
        "verification_checks": verification_checks,
        "confidence": confidence,
        "assessment": assessment or (
            "Causal relationship requires field "
            "verification before confirmation."
        )
    }
