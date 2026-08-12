from predictive_history import get_predictions


def build_prediction_performance(
    equipment_tag=None
):
    """
    Calculate historical Anvi prediction performance.

    Accuracy is based only on VERIFIED predictions.
    PENDING predictions are excluded from accuracy.
    """

    if equipment_tag:
        records = get_predictions(
            equipment_tag
        )
    else:
        records = []

    total = len(records)

    pending = sum(
        1 for r in records
        if r.get("verification_status") == "PENDING"
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

    verified_count = len(verified)

    if verified_count:
        accuracy = (
            correct / verified_count
        ) * 100
    else:
        accuracy = 0

    if accuracy >= 90 and verified_count >= 3:
        performance = "EXCELLENT"

    elif accuracy >= 75 and verified_count >= 3:
        performance = "GOOD"

    elif accuracy >= 50 and verified_count >= 2:
        performance = "DEVELOPING"

    elif verified_count == 0:
        performance = "NO VERIFIED DATA"

    else:
        performance = "INSUFFICIENT DATA"

    return {
        "equipment": equipment_tag,
        "total_predictions": total,
        "verified_predictions": verified_count,
        "pending_predictions": pending,
        "correct": correct,
        "partial": partial,
        "incorrect": incorrect,
        "accuracy_percentage": round(
            accuracy,
            1
        ),
        "performance": performance,
        "message": (
            "Prediction performance is based only "
            "on verified outcomes."
        )
    }
