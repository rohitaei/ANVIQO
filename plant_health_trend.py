from plant_health_history import get_plant_history


def analyze_plant_health_trend(plant_name):
    """
    Analyze the historical direction of plant health.
    """

    history = get_plant_history(plant_name)

    if len(history) < 2:
        return {
            "status": "INSUFFICIENT DATA",
            "trend": "UNKNOWN",
            "message": (
                "At least two health records "
                "are required."
            )
        }

    scores = []

    for record in history:

        try:
            scores.append(
                float(record["health_score"])
            )
        except (KeyError, TypeError, ValueError):
            continue

    if len(scores) < 2:
        return {
            "status": "INSUFFICIENT DATA",
            "trend": "UNKNOWN",
            "message": "Not enough valid health records."
        }

    first = scores[0]
    last = scores[-1]

    total_change = round(last - first, 2)

    increases = 0
    decreases = 0
    stable = 0

    for i in range(1, len(scores)):

        change = scores[i] - scores[i - 1]

        if change > 0:
            increases += 1

        elif change < 0:
            decreases += 1

        else:
            stable += 1

    intervals = len(scores) - 1

    if decreases == intervals:
        trend = "CONSISTENTLY DETERIORATING"

    elif increases == intervals:
        trend = "CONSISTENTLY IMPROVING"

    elif decreases > increases:
        trend = "GENERALLY DETERIORATING"

    elif increases > decreases:
        trend = "GENERALLY IMPROVING"

    else:
        trend = "FLUCTUATING"

    if total_change <= -15:
        status = "HIGH CONCERN"

    elif total_change <= -5:
        status = "ATTENTION"

    elif total_change >= 5:
        status = "IMPROVING"

    else:
        status = "STABLE"

    return {
        "first_health": first,
        "last_health": last,
        "total_change": total_change,
        "records_analyzed": len(scores),
        "increases": increases,
        "decreases": decreases,
        "stable_intervals": stable,
        "trend": trend,
        "status": status,
        "message": (
            f"Plant health changed by "
            f"{total_change} points and is "
            f"{trend.lower()}."
        )
    }
