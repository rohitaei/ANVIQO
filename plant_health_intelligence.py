from datetime import datetime


def build_plant_health_intelligence(
    plant_name,
    area_results
):
    """
    Explain why overall plant health has its current condition.
    """

    if not area_results:
        return {
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
            "plant": plant_name,
            "status": "NO DATA",
            "health_score": None,
            "critical_areas": [],
            "degraded_areas": [],
            "healthy_areas": [],
            "contributors": [],
            "explanation": "No area health data available."
        }

    valid = [
        area for area in area_results
        if area.get("health_score") is not None
    ]

    if not valid:
        return {
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
            "plant": plant_name,
            "status": "NO DATA",
            "health_score": None,
            "critical_areas": [],
            "degraded_areas": [],
            "healthy_areas": [],
            "contributors": [],
            "explanation": "No valid area health data available."
        }

    scores = [
        float(area["health_score"])
        for area in valid
    ]

    health_score = round(
        sum(scores) / len(scores),
        2
    )

    critical = [
        area for area in valid
        if str(area.get("status", "")).upper()
        == "CRITICAL"
    ]

    degraded = [
        area for area in valid
        if str(area.get("status", "")).upper()
        == "DEGRADED"
    ]

    healthy = [
        area for area in valid
        if str(area.get("status", "")).upper()
        in ("HEALTHY", "WATCH")
    ]

    contributors = []

    for area in critical:
        contributors.append({
            "area": area.get("area", "UNKNOWN"),
            "health_score": area.get("health_score"),
            "status": "CRITICAL",
            "severity": "HIGH"
        })

    for area in degraded:
        contributors.append({
            "area": area.get("area", "UNKNOWN"),
            "health_score": area.get("health_score"),
            "status": "DEGRADED",
            "severity": "MEDIUM"
        })

    if critical:
        status = "CRITICAL"

        names = ", ".join(
            str(area.get("area", "UNKNOWN"))
            for area in critical
        )

        explanation = (
            f"Plant health is critical because "
            f"{len(critical)} area(s) are critical: "
            f"{names}. "
            f"Overall health score is {health_score}."
        )

    elif degraded:
        status = "DEGRADED"

        names = ", ".join(
            str(area.get("area", "UNKNOWN"))
            for area in degraded
        )

        explanation = (
            f"Plant health is degraded because "
            f"{len(degraded)} area(s) require attention: "
            f"{names}. "
            f"Overall health score is {health_score}."
        )

    elif health_score < 80:
        status = "WATCH"

        explanation = (
            f"Plant health is under observation. "
            f"Overall health score is {health_score}."
        )

    else:
        status = "HEALTHY"

        explanation = (
            f"Plant health is healthy with an "
            f"overall score of {health_score}."
        )

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "plant": plant_name,
        "status": status,
        "health_score": health_score,
        "critical_areas": critical,
        "degraded_areas": degraded,
        "healthy_areas": healthy,
        "contributors": contributors,
        "explanation": explanation
    }
