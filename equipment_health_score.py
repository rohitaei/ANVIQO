def calculate_health_score(
    risk_score,
    criticality="MEDIUM",
    trend_status="STABLE",
    event_count=0
):
    """
    Calculate a stable, explainable equipment health score.

    100 = healthiest
    0   = most critical
    """

    try:
        risk = float(risk_score)
    except (TypeError, ValueError):
        risk = 0

    risk = max(0, min(100, risk))

    # Base health comes directly from risk.
    health = 100 - risk

    # Small contextual adjustments only.
    criticality = str(criticality).upper()
    trend_status = str(trend_status).upper()

    if criticality == "HIGH":
        health -= 3
    elif criticality == "CRITICAL":
        health -= 5

    if trend_status == "DETERIORATING":
        health -= 5
    elif trend_status == "IMPROVING":
        health += 3

    # Repeated events indicate instability,
    # but their effect is deliberately limited.
    if event_count >= 5:
        health -= 4
    elif event_count >= 3:
        health -= 2

    health = max(0, min(100, round(health)))

    if health >= 80:
        status = "HEALTHY"
    elif health >= 60:
        status = "WATCH"
    elif health >= 40:
        status = "DEGRADED"
    else:
        status = "CRITICAL"

    return {
        "health_score": health,
        "health_status": status,
        "risk_score": risk,
        "criticality": criticality,
        "trend_status": trend_status,
        "event_count": event_count
    }


def build_health_assessment(
    tag,
    equipment_name,
    risk_score,
    criticality,
    trend_status,
    event_count,
    contributors=None
):
    result = calculate_health_score(
        risk_score,
        criticality,
        trend_status,
        event_count
    )

    return {
        "equipment": tag,
        "name": equipment_name,
        "health": result,
        "contributors": contributors or []
    }
