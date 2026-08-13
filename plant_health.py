from trend_engine import analyze_trend


def analyze_plant(parameters):
    """
    Existing Anviqo plant parameter analysis.
    Preserved for compatibility.
    """

    results = []
    warnings = []

    for name, values in parameters.items():

        result = analyze_trend(values, name)

        results.append(result)

        if result["status"] in ("EARLY WARNING", "WATCH"):
            warnings.append(result)

    if not warnings:
        overall = "NORMAL"
        message = "No significant parameter trend detected."

    elif any(
        r["status"] == "EARLY WARNING"
        for r in warnings
    ):
        overall = "ATTENTION REQUIRED"
        message = (
            f"{len(warnings)} parameter(s) require attention."
        )

    else:
        overall = "WATCH"
        message = (
            f"{len(warnings)} parameter(s) should be monitored."
        )

    return {
        "overall_status": overall,
        "message": message,
        "parameters": results
    }


def calculate_plant_health(area_list):
    """
    Calculate overall plant health from area health scores.
    """

    if not area_list:
        return {
            "health_score": None,
            "status": "NO DATA",
            "area_count": 0,
            "message": "No area health data available."
        }

    valid = []

    for area in area_list:

        try:
            score = float(area.get("health_score"))
        except (TypeError, ValueError):
            continue

        score = max(0, min(100, score))

        valid.append({
            "area": area.get("area", "UNKNOWN"),
            "health_score": score,
            "status": area.get("status", "UNKNOWN")
        })

    if not valid:
        return {
            "health_score": None,
            "status": "NO DATA",
            "area_count": 0,
            "message": "No valid area health data."
        }

    average = sum(
        area["health_score"]
        for area in valid
    ) / len(valid)

    average = round(average, 2)

    critical_areas = sum(
        1
        for area in valid
        if area["status"] == "CRITICAL"
    )

    degraded_areas = sum(
        1
        for area in valid
        if area["status"] == "DEGRADED"
    )

    if average >= 80 and critical_areas == 0:
        status = "HEALTHY"

    elif average >= 60 and critical_areas == 0:
        status = "WATCH"

    elif average >= 40:
        status = "DEGRADED"

    else:
        status = "CRITICAL"

    return {
        "health_score": average,
        "status": status,
        "area_count": len(valid),
        "critical_areas": critical_areas,
        "degraded_areas": degraded_areas,
        "areas": valid,
        "message": (
            f"Plant health is {status.lower()} "
            f"with an average health score of {average}."
        )
    }


def build_plant_health(plant_name, area_list):
    """
    Build a complete plant health assessment.
    """

    result = calculate_plant_health(area_list)

    return {
        "plant": plant_name,
        "health": result
    }
