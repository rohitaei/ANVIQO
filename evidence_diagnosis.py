from datetime import datetime


def diagnose_equipment(
    equipment,
    parameter_events=None,
    correlation=None,
    health=None,
    risk=None
):
    """
    ANVIQO V5.0.8
    Evidence-backed equipment diagnosis.

    Read-only advisory engine.
    Does not send commands to PLC/DCS.
    """

    parameter_events = parameter_events or []
    correlation = correlation or {}
    health = health or {}
    risk = risk or {}

    tag = equipment.get("tag", "UNKNOWN")
    name = equipment.get("name", "Equipment")
    equipment_type = equipment.get("type", "UNKNOWN")
    criticality = equipment.get(
        "criticality",
        "MEDIUM"
    )

    observations = []
    causes = []
    checks = []
    safety = []

    # ---------------------------------
    # Detect observed parameter changes
    # ---------------------------------

    air_pressure_drop = False
    valve_position_rise = False
    temperature_rise = False

    for event in parameter_events:

        message = str(
            event.get("message", "")
        )

        observations.append(message)

        text = message.lower()

        if (
            "air pressure" in text
            and "decreased" in text
        ):
            air_pressure_drop = True

        if (
            "valve position" in text
            and "increased" in text
        ):
            valve_position_rise = True

        if (
            "temperature" in text
            and "increased" in text
        ):
            temperature_rise = True

    # ---------------------------------
    # Technical reasoning
    # ---------------------------------

    if air_pressure_drop:

        causes.append({
            "cause": "Instrument air supply degradation",
            "reason": (
                "Reduced instrument air pressure can "
                "affect actuator or positioner response."
            ),
            "confidence": 85
        })

        checks.extend([
            "Check instrument air pressure at the positioner.",
            "Check air filter/regulator condition.",
            "Check for leakage in the actuator air circuit."
        ])

    if valve_position_rise:

        causes.append({
            "cause": "Control valve or positioner degradation",
            "reason": (
                "Increasing valve demand or position "
                "may indicate a developing control problem."
            ),
            "confidence": 80
        })

        checks.extend([
            "Verify valve command versus actual position.",
            "Check positioner feedback.",
            "Inspect actuator and valve stem movement.",
            "Check for mechanical sticking."
        ])

    if temperature_rise:

        causes.append({
            "cause": "Process condition deterioration",
            "reason": (
                "Increasing temperature may indicate "
                "a developing process or control deviation."
            ),
            "confidence": 65
        })

        checks.append(
            "Verify the temperature measurement "
            "and compare with process operating conditions."
        )

    # ---------------------------------
    # Correlation evidence
    # ---------------------------------

    correlation_status = correlation.get(
        "status",
        "NO CORRELATION"
    )

    if correlation_status in (
        "CORRELATED CONDITION",
        "POSSIBLE CORRELATION"
    ):

        observations.append(
            correlation.get(
                "correlation",
                "Related events detected."
            )
        )

    # ---------------------------------
    # Health and risk evidence
    # ---------------------------------

    risk_score = risk.get(
        "risk_score"
    )

    health_score = health.get(
        "health_score"
    )

    if risk_score is not None:

        observations.append(
            f"Equipment risk score is {risk_score}."
        )

    if health_score is not None:

        observations.append(
            f"Equipment health score is {health_score}."
        )

    # ---------------------------------
    # Determine diagnosis
    # ---------------------------------

    if (
        air_pressure_drop
        and valve_position_rise
    ):

        diagnosis = (
            "Likely control-valve/positioner or "
            "instrument-air degradation."
        )

        diagnosis_confidence = 90

    elif valve_position_rise:

        diagnosis = (
            "Possible control-valve or positioner "
            "performance degradation."
        )

        diagnosis_confidence = 80

    elif air_pressure_drop:

        diagnosis = (
            "Possible instrument-air supply "
            "degradation affecting equipment response."
        )

        diagnosis_confidence = 80

    elif temperature_rise:

        diagnosis = (
            "Possible process or measurement "
            "condition requiring investigation."
        )

        diagnosis_confidence = 65

    else:

        diagnosis = (
            "Insufficient evidence for a specific "
            "technical diagnosis."
        )

        diagnosis_confidence = 30

    # ---------------------------------
    # Safety guidance
    # ---------------------------------

    safety.extend([
        "Do not bypass interlocks or protection systems.",
        "Follow site permit and isolation procedures.",
        "Confirm process conditions before physical inspection.",
        "Do not manipulate control equipment solely from this advisory."
    ])

    # ---------------------------------
    # Missing information
    # ---------------------------------

    missing = []

    if not parameter_events:
        missing.append(
            "Recent parameter history"
        )

    if risk_score is None:
        missing.append(
            "Current risk score"
        )

    if health_score is None:
        missing.append(
            "Current health score"
        )

    if not correlation:
        missing.append(
            "Event correlation data"
        )

    # ---------------------------------
    # Evidence strength
    # ---------------------------------

    evidence_count = 0

    if parameter_events:
        evidence_count += 1

    if risk_score is not None:
        evidence_count += 1

    if health_score is not None:
        evidence_count += 1

    if correlation_status in (
        "CORRELATED CONDITION",
        "POSSIBLE CORRELATION"
    ):
        evidence_count += 1

    if evidence_count >= 4:
        evidence_strength = "STRONG"
    elif evidence_count >= 2:
        evidence_strength = "MODERATE"
    elif evidence_count == 1:
        evidence_strength = "WEAK"
    else:
        evidence_strength = "INSUFFICIENT"

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": tag,
        "equipment_name": name,
        "equipment_type": equipment_type,
        "criticality": criticality,
        "diagnosis": diagnosis,
        "diagnosis_confidence": diagnosis_confidence,
        "observations": observations,
        "likely_causes": causes,
        "recommended_checks": checks,
        "safety": safety,
        "missing_information": missing,
        "evidence": {
            "count": evidence_count,
            "strength": evidence_strength
        },
        "read_only": True
    }
