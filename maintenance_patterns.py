from maintenance_actions import (
    load_actions
)


VALID_OUTCOMES = {
    "IMPROVED",
    "UNCHANGED",
    "WORSENED",
    "UNKNOWN"
}


def normalize_pattern(text):
    """
    Convert a prediction/action description into
    a simple reusable maintenance pattern.
    """

    if not text:
        return "UNKNOWN"

    text = str(
        text
    ).upper()

    if (
        "INSTRUMENT-AIR" in text
        or "INSTRUMENT AIR" in text
        or "AIR PRESSURE" in text
    ):
        return "INSTRUMENT AIR"

    if (
        "POSITIONER" in text
        or "I/P" in text
    ):
        return "POSITIONER / I-P"

    if (
        "CONTROL VALVE" in text
        or "VALVE" in text
    ):
        return "CONTROL VALVE"

    if (
        "TEMPERATURE" in text
        or "TEMPERATURE INCREASE" in text
    ):
        return "TEMPERATURE"

    return "GENERAL MAINTENANCE"


def build_maintenance_patterns():
    """
    Group VERIFIED maintenance actions by
    maintenance pattern.
    """

    data = load_actions()

    patterns = {}

    for equipment, records in data.items():

        for record in records:

            if record.get(
                "status"
            ) != "VERIFIED":
                continue

            outcome = str(
                record.get(
                    "outcome",
                    "UNKNOWN"
                )
            ).strip().upper()

            if outcome not in VALID_OUTCOMES:
                outcome = "UNKNOWN"

            source = record.get(
                "source_prediction"
            )

            action = record.get(
                "action"
            )

            pattern = normalize_pattern(
                (
                    str(source or "")
                    + " "
                    + str(action or "")
                )
            )

            if pattern not in patterns:

                patterns[pattern] = {
                    "pattern": pattern,
                    "verified_actions": 0,
                    "improved": 0,
                    "unchanged": 0,
                    "worsened": 0,
                    "unknown": 0,
                    "equipment": [],
                    "actions": []
                }

            result = patterns[
                pattern
            ]

            result[
                "verified_actions"
            ] += 1

            if outcome == "IMPROVED":
                result["improved"] += 1

            elif outcome == "UNCHANGED":
                result["unchanged"] += 1

            elif outcome == "WORSENED":
                result["worsened"] += 1

            else:
                result["unknown"] += 1

            if equipment not in result[
                "equipment"
            ]:
                result[
                    "equipment"
                ].append(
                    equipment
                )

            result[
                "actions"
            ].append({
                "equipment": equipment,
                "action": action,
                "outcome": outcome,
                "verified_at": record.get(
                    "verified_at"
                )
            })

    output = []

    for pattern, result in patterns.items():

        total = result[
            "verified_actions"
        ]

        if total:

            result[
                "improvement_rate"
            ] = round(
                (
                    result["improved"]
                    / total
                ) * 100,
                1
            )

        else:

            result[
                "improvement_rate"
            ] = 0

        if total >= 5:

            if result[
                "improvement_rate"
            ] >= 80:

                result[
                    "evidence_status"
                ] = "STRONG"

            elif result[
                "improvement_rate"
            ] >= 60:

                result[
                    "evidence_status"
                ] = "MODERATE"

            else:

                result[
                    "evidence_status"
                ] = "WEAK"

        else:

            result[
                "evidence_status"
            ] = "INSUFFICIENT DATA"

        output.append(
            result
        )

    return {
        "pattern_count": len(
            output
        ),
        "patterns": output
    }
