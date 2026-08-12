from predictive_history import (
    load_predictions,
    save_predictions
)


def save_confidence_prediction(
    prediction_record
):
    """
    Persist a confidence-aware prediction
    into Anvi prediction history.

    Existing records are preserved.
    """

    if not isinstance(
        prediction_record,
        dict
    ):
        return {
            "success": False,
            "message": (
                "Prediction record must be a dictionary."
            )
        }

    equipment_tag = prediction_record.get(
        "equipment"
    )

    if not equipment_tag:
        return {
            "success": False,
            "message": "Equipment tag is required."
        }

    predictions = load_predictions()

    if equipment_tag not in predictions:
        predictions[equipment_tag] = []

    # Prevent accidental duplicate timestamps.
    timestamp = prediction_record.get(
        "timestamp"
    )

    for existing in predictions[equipment_tag]:

        if (
            timestamp
            and existing.get("timestamp")
            == timestamp
        ):
            return {
                "success": False,
                "message": (
                    "Prediction with this timestamp "
                    "already exists."
                )
            }

    # Ensure verification fields exist.
    prediction_record.setdefault(
        "verification_status",
        "PENDING"
    )

    prediction_record.setdefault(
        "actual_outcome",
        None
    )

    prediction_record.setdefault(
        "prediction_accuracy",
        None
    )

    predictions[
        equipment_tag
    ].append(
        prediction_record
    )

    save_predictions(
        predictions
    )

    return {
        "success": True,
        "prediction": prediction_record
    }


def get_confidence_prediction_history(
    equipment_tag
):
    """
    Return all prediction records for equipment.
    """

    predictions = load_predictions()

    records = predictions.get(
        equipment_tag,
        []
    )

    return {
        "equipment": equipment_tag,
        "prediction_count": len(records),
        "predictions": records
    }
