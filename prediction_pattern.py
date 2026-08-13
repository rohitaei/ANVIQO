from predictive_history import load_predictions


def classify_prediction(record):
    """
    Classify a prediction into a broad industrial
    prediction pattern.

    This is classification, not a failure diagnosis.
    """

    text_parts = []

    text_parts.append(
        str(record.get("prediction", ""))
    )

    text_parts.append(
        str(record.get("likely_development", ""))
    )

    text_parts.extend(
        str(item)
        for item in record.get(
            "evidence",
            []
        )
    )

    text = " ".join(
        text_parts
    ).lower()

    if (
        "air pressure" in text
        or "instrument-air" in text
        or "instrument air" in text
    ):
        return "INSTRUMENT AIR"

    if (
        "positioner" in text
        or "i/p" in text
        or "control-valve" in text
        or "control valve" in text
    ):
        return "CONTROL VALVE / POSITIONER"

    if (
        "temperature" in text
        or "thermal" in text
    ):
        return "TEMPERATURE"

    if (
        "pressure" in text
        or "pressure" in text
    ):
        return "PRESSURE"

    if (
        "flow" in text
        or "flowrate" in text
    ):
        return "FLOW"

    return "OTHER"


def build_pattern_performance():
    """
    Calculate verified prediction performance
    by prediction pattern.
    """

    predictions = load_predictions()

    patterns = {}

    for equipment_tag, records in predictions.items():

        for record in records:

            pattern = classify_prediction(
                record
            )

            if pattern not in patterns:
                patterns[pattern] = {
                    "pattern": pattern,
                    "total_predictions": 0,
                    "verified_predictions": 0,
                    "pending_predictions": 0,
                    "correct": 0,
                    "partial": 0,
                    "incorrect": 0
                }

            result = patterns[pattern]

            result["total_predictions"] += 1

            if (
                record.get(
                    "verification_status"
                ) == "PENDING"
            ):
                result[
                    "pending_predictions"
                ] += 1

            elif (
                record.get(
                    "verification_status"
                ) == "VERIFIED"
            ):

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

    for pattern in sorted(
        patterns.keys()
    ):

        result = patterns[pattern]

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

        if verified >= 3:

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

        result[
            "accuracy_percentage"
        ] = round(
            accuracy,
            1
        )

        result[
            "performance"
        ] = performance

        output.append(
            result
        )

    return {
        "pattern_count": len(output),
        "patterns": output
    }
