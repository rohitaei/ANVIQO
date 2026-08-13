from datetime import datetime
from predictive_history import (
    get_predictions,
    update_prediction_outcome
)


VALID_OUTCOMES = {
    "CORRECT",
    "PARTIAL",
    "INCORRECT"
}


def verify_prediction(
    equipment_tag,
    prediction_timestamp,
    actual_outcome,
    outcome_status
):
    """
    Verify a previously stored Anvi prediction.

    outcome_status must be:
    CORRECT, PARTIAL, or INCORRECT.
    """

    status = str(
        outcome_status
    ).strip().upper()

    if status not in VALID_OUTCOMES:
        return {
            "success": False,
            "message": (
                "Invalid outcome status. "
                "Use CORRECT, PARTIAL or INCORRECT."
            )
        }

    if not actual_outcome:
        return {
            "success": False,
            "message": "Actual outcome is required."
        }

    records = get_predictions(
        equipment_tag
    )

    target = None

    for record in records:
        if record.get("timestamp") == prediction_timestamp:
            target = record
            break

    if target is None:
        return {
            "success": False,
            "message": "Prediction record not found."
        }

    result = update_prediction_outcome(
        equipment_tag,
        prediction_timestamp,
        actual_outcome,
        status
    )

    if not result.get("success"):
        return result

    verified_record = result["record"]

    return {
        "success": True,
        "verified_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment_tag,
        "prediction_timestamp": prediction_timestamp,
        "prediction_level": verified_record.get(
            "prediction_level"
        ),
        "verification_status": "VERIFIED",
        "actual_outcome": actual_outcome,
        "prediction_accuracy": status
    }


def get_verification_summary(
    equipment_tag
):
    """
    Summarize verified prediction accuracy.
    """

    records = get_predictions(
        equipment_tag
    )

    verified = [
        r for r in records
        if r.get("verification_status") == "VERIFIED"
    ]

    correct = sum(
        1 for r in verified
        if r.get("prediction_accuracy") == "CORRECT"
    )

    partial = sum(
        1 for r in verified
        if r.get("prediction_accuracy") == "PARTIAL"
    )

    incorrect = sum(
        1 for r in verified
        if r.get("prediction_accuracy") == "INCORRECT"
    )

    if verified:
        accuracy_percentage = (
            correct / len(verified)
        ) * 100
    else:
        accuracy_percentage = 0

    return {
        "equipment": equipment_tag,
        "total_predictions": len(records),
        "verified_predictions": len(verified),
        "correct": correct,
        "partial": partial,
        "incorrect": incorrect,
        "accuracy_percentage": round(
            accuracy_percentage,
            1
        )
    }
