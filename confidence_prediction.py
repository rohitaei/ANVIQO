from datetime import datetime


VALID_LEVELS = {
    "HIGH",
    "MEDIUM",
    "LOW"
}


def build_confidence_prediction(
    equipment_tag,
    equipment_name,
    prediction,
    confidence_level,
    confidence_score,
    evidence_quality,
    evidence=None,
    reasoning=None,
    likely_development=None
):
    """
    Build a new confidence-aware prediction record.

    This does not modify existing prediction history.
    """

    level = str(
        confidence_level
    ).strip().upper()

    if level not in VALID_LEVELS:
        return {
            "success": False,
            "message": (
                "Confidence level must be "
                "HIGH, MEDIUM or LOW."
            )
        }

    try:
        score = float(
            confidence_score
        )
    except (TypeError, ValueError):
        return {
            "success": False,
            "message": (
                "Confidence score must be numeric."
            )
        }

    if score < 0 or score > 100:
        return {
            "success": False,
            "message": (
                "Confidence score must be "
                "between 0 and 100."
            )
        }

    if not evidence_quality:
        evidence_quality = "UNKNOWN"

    record = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment_tag,
        "equipment_name": equipment_name,
        "prediction": prediction,
        "confidence_level": level,
        "confidence_score": score,
        "evidence_quality": evidence_quality,
        "evidence": evidence or [],
        "reasoning": reasoning or [],
        "likely_development": (
            likely_development
            or "Not specified."
        ),
        "verification_status": "PENDING",
        "actual_outcome": None,
        "prediction_accuracy": None
    }

    return {
        "success": True,
        "prediction": record
    }
