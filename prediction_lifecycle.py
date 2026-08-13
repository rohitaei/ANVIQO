from datetime import datetime

from confidence_prediction import (
    build_confidence_prediction
)

from confidence_prediction_history import (
    save_confidence_prediction,
    get_confidence_prediction_history
)

from prediction_verification import (
    verify_prediction
)


VALID_STATUSES = {
    "PENDING",
    "VERIFIED"
}

VALID_ACCURACY = {
    "CORRECT",
    "PARTIAL",
    "INCORRECT"
}


def create_prediction(
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
    Create and persist a new Anvi prediction.
    """

    result = build_confidence_prediction(
        equipment_tag,
        equipment_name,
        prediction,
        confidence_level,
        confidence_score,
        evidence_quality,
        evidence,
        reasoning,
        likely_development
    )

    if not result.get("success"):
        return result

    save_result = save_confidence_prediction(
        result["prediction"]
    )

    if not save_result.get("success"):
        return save_result

    return {
        "success": True,
        "action": "CREATED",
        "prediction": result["prediction"]
    }


def get_prediction(
    equipment_tag,
    timestamp
):
    """
    Retrieve one prediction by timestamp.
    """

    history = get_confidence_prediction_history(
        equipment_tag
    )

    for record in history["predictions"]:

        if record.get(
            "timestamp"
        ) == timestamp:

            return record

    return None


def get_pending_predictions(
    equipment_tag=None
):
    """
    Return pending predictions.

    If equipment_tag is supplied, only that
    equipment is searched.
    """

    if equipment_tag:

        records = get_confidence_prediction_history(
            equipment_tag
        )["predictions"]

        return [
            record
            for record in records
            if record.get(
                "verification_status"
            ) == "PENDING"
        ]

    return []


def verify_prediction_lifecycle(
    equipment_tag,
    timestamp,
    actual_outcome,
    accuracy
):
    """
    Verify a pending prediction and record
    the real-world outcome.
    """

    accuracy = str(
        accuracy
    ).strip().upper()

    if accuracy not in VALID_ACCURACY:

        return {
            "success": False,
            "message": (
                "Accuracy must be CORRECT, "
                "PARTIAL or INCORRECT."
            )
        }

    record = get_prediction(
        equipment_tag,
        timestamp
    )

    if record is None:

        return {
            "success": False,
            "message": "Prediction not found."
        }

    if record.get(
        "verification_status"
    ) == "VERIFIED":

        return {
            "success": False,
            "message": (
                "Prediction has already been verified."
            )
        }

    result = verify_prediction(
        equipment_tag,
        timestamp,
        actual_outcome,
        accuracy
    )

    return result


def build_prediction_lifecycle(
    equipment_tag
):
    """
    Return the complete prediction lifecycle
    for equipment.
    """

    history = get_confidence_prediction_history(
        equipment_tag
    )

    records = history[
        "predictions"
    ]

    pending = [
        r for r in records
        if r.get(
            "verification_status"
        ) == "PENDING"
    ]

    verified = [
        r for r in records
        if r.get(
            "verification_status"
        ) == "VERIFIED"
    ]

    return {
        "equipment": equipment_tag,
        "total_predictions": len(records),
        "pending": len(pending),
        "verified": len(verified),
        "predictions": records,
        "lifecycle_status": (
            "VERIFICATION REQUIRED"
            if pending
            else "UP TO DATE"
        ),
        "generated_at": datetime.now().isoformat(
            timespec="seconds"
        )
    }
