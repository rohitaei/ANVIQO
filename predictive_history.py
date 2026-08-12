import json
import os
from datetime import datetime

DB_FILE = os.path.join(
    "database",
    "predictive_alerts.json"
)


def ensure_database():
    os.makedirs("database", exist_ok=True)

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f, indent=4)


def load_predictions():
    ensure_database()

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {}

        return data

    except (json.JSONDecodeError, OSError):
        return {}


def save_predictions(data):
    ensure_database()

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


def record_prediction(
    equipment_tag,
    prediction_level,
    health_score,
    risk_score,
    prediction,
    evidence=None,
    likely_development=None
):
    """
    Store an Anvi predictive warning.
    """

    if not equipment_tag:
        return {
            "success": False,
            "message": "Equipment tag is required."
        }

    predictions = load_predictions()

    if equipment_tag not in predictions:
        predictions[equipment_tag] = []

    record = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment_tag,
        "prediction_level": prediction_level,
        "health_score": health_score,
        "risk_score": risk_score,
        "prediction": prediction,
        "evidence": evidence or [],
        "likely_development": (
            likely_development
            or "Not specified."
        ),
        "verification_status": "PENDING",
        "actual_outcome": None,
        "prediction_accuracy": None
    }

    predictions[equipment_tag].append(record)

    save_predictions(predictions)

    return {
        "success": True,
        "prediction": record
    }


def get_predictions(equipment_tag):
    predictions = load_predictions()

    return predictions.get(
        equipment_tag,
        []
    )


def get_latest_prediction(equipment_tag):
    records = get_predictions(equipment_tag)

    if not records:
        return None

    return records[-1]


def update_prediction_outcome(
    equipment_tag,
    timestamp,
    actual_outcome,
    prediction_accuracy
):
    """
    Record what actually happened after a prediction.
    """

    predictions = load_predictions()

    records = predictions.get(
        equipment_tag,
        []
    )

    for record in records:

        if record.get("timestamp") == timestamp:

            record["verification_status"] = (
                "VERIFIED"
            )

            record["actual_outcome"] = (
                actual_outcome
            )

            record["prediction_accuracy"] = (
                prediction_accuracy
            )

            save_predictions(predictions)

            return {
                "success": True,
                "record": record
            }

    return {
        "success": False,
        "message": "Prediction record not found."
    }


def build_prediction_history(
    equipment_tag
):
    records = get_predictions(
        equipment_tag
    )

    return {
        "equipment": equipment_tag,
        "prediction_count": len(records),
        "predictions": records
    }
