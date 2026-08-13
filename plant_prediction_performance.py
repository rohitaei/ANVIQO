import json
import os

from predictive_history import load_predictions


def build_equipment_performance(equipment_tag):
    """
    Build prediction performance for one equipment.
    """

    predictions = load_predictions()

    records = predictions.get(
        equipment_tag,
        []
    )

    total = len(records)

    verified = [
        r for r in records
        if r.get("verification_status") == "VERIFIED"
    ]

    pending = [
        r for r in records
        if r.get("verification_status") == "PENDING"
    ]

    correct = sum(
        1
        for r in verified
        if r.get("prediction_accuracy") == "CORRECT"
    )

    partial = sum(
        1
        for r in verified
        if r.get("prediction_accuracy") == "PARTIAL"
    )

    incorrect = sum(
        1
        for r in verified
        if r.get("prediction_accuracy") == "INCORRECT"
    )

    verified_count = len(verified)

    if verified_count:
        accuracy = (
            correct / verified_count
        ) * 100
    else:
        accuracy = 0

    if verified_count >= 3:

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
        "equipment": equipment_tag,
        "total_predictions": total,
        "verified_predictions": verified_count,
        "pending_predictions": len(pending),
        "correct": correct,
        "partial": partial,
        "incorrect": incorrect,
        "accuracy_percentage": round(
            accuracy,
            1
        ),
        "performance": performance
    }


def build_plant_prediction_performance():
    """
    Build prediction performance across all
    equipment currently present in prediction history.
    """

    predictions = load_predictions()

    equipment_results = []

    for tag in sorted(
        predictions.keys()
    ):

        result = build_equipment_performance(
            tag
        )

        equipment_results.append(
            result
        )

    total_predictions = sum(
        r["total_predictions"]
        for r in equipment_results
    )

    total_verified = sum(
        r["verified_predictions"]
        for r in equipment_results
    )

    total_pending = sum(
        r["pending_predictions"]
        for r in equipment_results
    )

    total_correct = sum(
        r["correct"]
        for r in equipment_results
    )

    total_partial = sum(
        r["partial"]
        for r in equipment_results
    )

    total_incorrect = sum(
        r["incorrect"]
        for r in equipment_results
    )

    if total_verified:
        overall_accuracy = (
            total_correct
            / total_verified
        ) * 100
    else:
        overall_accuracy = 0

    if total_verified >= 5:

        if overall_accuracy >= 90:
            overall_performance = "EXCELLENT"

        elif overall_accuracy >= 75:
            overall_performance = "GOOD"

        elif overall_accuracy >= 50:
            overall_performance = "DEVELOPING"

        else:
            overall_performance = "POOR"

    else:
        overall_performance = "INSUFFICIENT DATA"

    return {
        "plant": "Tata Steel Plant",
        "equipment_count": len(
            equipment_results
        ),
        "total_predictions": total_predictions,
        "verified_predictions": total_verified,
        "pending_predictions": total_pending,
        "correct": total_correct,
        "partial": total_partial,
        "incorrect": total_incorrect,
        "accuracy_percentage": round(
            overall_accuracy,
            1
        ),
        "performance": overall_performance,
        "equipment": equipment_results
    }
