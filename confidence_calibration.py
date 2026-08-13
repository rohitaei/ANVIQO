from predictive_history import load_predictions


VALID_LEVELS = {
    "HIGH",
    "MEDIUM",
    "LOW"
}


def get_confidence_level(record):
    """
    Read Anvi's stored confidence level.

    Older prediction records may not contain
    confidence information.
    """

    level = record.get(
        "confidence_level"
    )

    if not level:
        return None

    level = str(
        level
    ).strip().upper()

    if level not in VALID_LEVELS:
        return None

    return level


def build_confidence_calibration():
    """
    Analyze verified prediction outcomes by
    Anvi confidence level.

    Only VERIFIED predictions are used for
    calibration accuracy.
    """

    predictions = load_predictions()

    levels = {}

    for equipment_tag, records in predictions.items():

        for record in records:

            level = get_confidence_level(
                record
            )

            if level is None:
                continue

            if level not in levels:
                levels[level] = {
                    "confidence_level": level,
                    "total_predictions": 0,
                    "verified_predictions": 0,
                    "pending_predictions": 0,
                    "correct": 0,
                    "partial": 0,
                    "incorrect": 0
                }

            result = levels[level]

            result[
                "total_predictions"
            ] += 1

            status = record.get(
                "verification_status"
            )

            if status == "PENDING":

                result[
                    "pending_predictions"
                ] += 1

            elif status == "VERIFIED":

                result[
                    "verified_predictions"
                ] += 1

                accuracy = record.get(
                    "prediction_accuracy"
                )

                if accuracy == "CORRECT":
                    result["correct"] += 1

                elif accuracy == "PARTIAL":
                    result["partial"] += 1

                elif accuracy == "INCORRECT":
                    result["incorrect"] += 1

    output = []

    for level in sorted(
        levels.keys()
    ):

        result = levels[level]

        verified = result[
            "verified_predictions"
        ]

        correct = result[
            "correct"
        ]

        if verified:

            accuracy = (
                correct / verified
            ) * 100

        else:
            accuracy = 0

        result[
            "accuracy_percentage"
        ] = round(
            accuracy,
            1
        )

        if verified >= 5:

            if accuracy >= 90:
                calibration = "WELL CALIBRATED"

            elif accuracy >= 75:
                calibration = "REASONABLY CALIBRATED"

            elif accuracy >= 50:
                calibration = "NEEDS IMPROVEMENT"

            else:
                calibration = "POORLY CALIBRATED"

        else:
            calibration = "INSUFFICIENT DATA"

        result[
            "calibration"
        ] = calibration

        output.append(
            result
        )

    return {
        "confidence_levels": len(
            output
        ),
        "levels": output
    }


def add_confidence_to_prediction(
    record,
    confidence_level
):
    """
    Helper for future prediction generation.
    """

    level = str(
        confidence_level
    ).strip().upper()

    if level not in VALID_LEVELS:

        raise ValueError(
            "Confidence must be HIGH, MEDIUM or LOW."
        )

    record[
        "confidence_level"
    ] = level

    return record
