from maintenance_patterns import (
    normalize_pattern
)


def build_current_pattern(
    evidence=None,
    possible_causes=None,
    equipment=None
):
    """
    Convert current diagnostic evidence into
    reusable maintenance patterns.
    """

    evidence = evidence or []
    possible_causes = possible_causes or []

    text = " ".join(
        [
            str(item)
            for item in (
                evidence
                + possible_causes
            )
        ]
    )

    pattern = normalize_pattern(
        text
    )

    return {
        "equipment": equipment,
        "current_pattern": pattern,
        "evidence": evidence,
        "possible_causes": possible_causes
    }


def match_maintenance_context(
    current_evidence=None,
    possible_causes=None,
    equipment=None,
    historical_pattern=None
):
    """
    Compare the current condition with a
    historical maintenance pattern.
    """

    current = build_current_pattern(
        current_evidence,
        possible_causes,
        equipment
    )

    current_pattern = current[
        "current_pattern"
    ]

    requested_pattern = normalize_pattern(
        historical_pattern
    )

    matched = (
        current_pattern
        == requested_pattern
    )

    if matched:

        context_status = "MATCH"

        message = (
            "Current equipment evidence matches "
            "the historical maintenance pattern."
        )

    else:

        context_status = "NO MATCH"

        message = (
            "Current equipment evidence does not "
            "match the historical maintenance pattern."
        )

    return {
        "equipment": equipment,
        "historical_pattern":
            requested_pattern,
        "current_pattern":
            current_pattern,
        "context_status":
            context_status,
        "matched":
            matched,
        "message":
            message
    }
