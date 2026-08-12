from predictive_history import load_predictions
from equipment_database import load_equipment


def build_area_prediction_performance(area):
    """
    Calculate prediction performance for all equipment
    belonging to a specific plant area.
    """

    equipment = load_equipment()
    predictions = load_predictions()

    area_tags = []

    for item in equipment:

        if item.get("area") == area:
            tag = item.get("tag")

            if tag:
                area_tags.append(tag)

    total_predictions = 0
    verified_predictions = 0
    pending_predictions = 0
    correct = 0
    partial = 0
    incorrect = 0

    equipment_results = []

    for tag in sorted(area_tags):

        records = predictions.get(
            tag,
            []
        )

        verified = [
            r for r in records
            if r.get("verification_status") == "VERIFIED"
        ]

        pending = [
            r for r in records
            if r.get("verification_status") == "PENDING"
        ]

        tag_correct = sum(
            1
            for r in verified
            if r.get("prediction_accuracy") == "CORRECT"
        )

        tag_partial = sum(
            1
            for r in verified
            if r.get("prediction_accuracy") == "PARTIAL"
        )

        tag_incorrect = sum(
            1
            for r in verified
            if r.get("prediction_accuracy") == "INCORRECT"
        )

        tag_verified = len(verified)

        if tag_verified:
            tag_accuracy = (
                tag_correct
                / tag_verified
            ) * 100
        else:
            tag_accuracy = 0

        total_predictions += len(records)
        verified_predictions += tag_verified
        pending_predictions += len(pending)

        correct += tag_correct
        partial += tag_partial
        incorrect += tag_incorrect

        equipment_results.append({
            "equipment": tag,
            "predictions": len(records),
            "verified": tag_verified,
            "pending": len(pending),
            "correct": tag_correct,
            "partial": tag_partial,
            "incorrect": tag_incorrect,
            "accuracy_percentage": round(
                tag_accuracy,
                1
            )
        })

    if verified_predictions:
        accuracy = (
            correct
            / verified_predictions
        ) * 100
    else:
        accuracy = 0

    if verified_predictions >= 3:

        if accuracy >= 90:
            performance = "EXCELLENT"

        elif accuracy >= 75:
            performance = "GOOD"

        elif accuracy >= 50:
            performance = "DEVELOPING"

        else:
            performance = "POOR"

    else:
        performance = "INSUFFICIENT DATA"

    return {
        "area": area,
        "equipment_count": len(area_tags),
        "total_predictions": total_predictions,
        "verified_predictions": verified_predictions,
        "pending_predictions": pending_predictions,
        "correct": correct,
        "partial": partial,
        "incorrect": incorrect,
        "accuracy_percentage": round(
            accuracy,
            1
        ),
        "performance": performance,
        "equipment": equipment_results
    }


def build_all_area_prediction_performance():
    """
    Calculate prediction performance for every
    area represented in the equipment database.
    """

    equipment = load_equipment()

    areas = sorted({
        item.get("area")
        for item in equipment
        if item.get("area")
    })

    results = []

    for area in areas:

        results.append(
            build_area_prediction_performance(
                area
            )
        )

    return {
        "plant": "Tata Steel Plant",
        "area_count": len(results),
        "areas": results
    }
