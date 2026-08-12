from datetime import datetime


def generate_predictive_warning(
    equipment_tag,
    equipment_name,
    health_score,
    risk_score,
    trend_status,
    confidence_level,
    parameters=None,
    causal_chain=None
):
    """
    Generate a conditional predictive warning.

    This does NOT predict a guaranteed failure.
    It identifies possible continued deterioration
    if the observed pattern persists.
    """

    parameters = parameters or []
    causal_chain = causal_chain or {}

    early_indicators = []

    for parameter in parameters:

        name = parameter.get(
            "name",
            "Parameter"
        )

        percentage = parameter.get(
            "percentage_change",
            0
        )

        direction = parameter.get(
            "direction",
            "UNKNOWN"
        )

        status = parameter.get(
            "status",
            "NORMAL"
        )

        try:
            percentage = float(percentage)
        except (TypeError, ValueError):
            continue

        if (
            abs(percentage) >= 10
            or status in (
                "WATCH",
                "EARLY WARNING"
            )
        ):
            early_indicators.append(
                f"{name} {direction.lower()} "
                f"{percentage}%"
            )

    # ---------------------------------
    # Determine prediction level
    # ---------------------------------

    try:
        health = float(health_score)
    except (TypeError, ValueError):
        health = None

    try:
        risk = float(risk_score)
    except (TypeError, ValueError):
        risk = None

    if (
        health is not None
        and risk is not None
        and health <= 20
        and risk >= 80
        and trend_status == "DETERIORATING"
    ):
        prediction_level = "HIGH"

    elif (
        risk is not None
        and risk >= 60
        and trend_status in (
            "DETERIORATING",
            "CONSISTENTLY DETERIORATING"
        )
    ):
        prediction_level = "MEDIUM"

    elif early_indicators:
        prediction_level = "WATCH"

    else:
        prediction_level = "LOW"

    # ---------------------------------
    # Prediction statement
    # ---------------------------------

    if prediction_level == "HIGH":

        prediction = (
            "Continued equipment deterioration is "
            "possible if the current parameter trends "
            "persist."
        )

    elif prediction_level == "MEDIUM":

        prediction = (
            "Further deterioration may develop if "
            "the observed trends continue."
        )

    elif prediction_level == "WATCH":

        prediction = (
            "The observed parameter changes should "
            "be monitored for continued deterioration."
        )

    else:

        prediction = (
            "No strong predictive deterioration "
            "signal is currently detected."
        )

    # ---------------------------------
    # Likely development
    # ---------------------------------

    possible_causes = causal_chain.get(
        "possible_causes",
        []
    )

    if possible_causes:

        likely_development = (
            possible_causes[0]
        )

    else:

        likely_development = (
            "Further equipment degradation "
            "cannot be determined from the "
            "available evidence."
        )

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment_tag,
        "equipment_name": equipment_name,
        "prediction_level": prediction_level,
        "health_score": health_score,
        "risk_score": risk_score,
        "trend_status": trend_status,
        "confidence": confidence_level,
        "prediction": prediction,
        "early_indicators": early_indicators,
        "likely_development": likely_development,
        "field_verification_required": True,
        "note": (
            "This is a conditional warning based on "
            "observed trends and does not confirm "
            "future failure."
        )
    }
