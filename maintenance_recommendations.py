from maintenance_patterns import (
    build_maintenance_patterns,
    normalize_pattern
)


def build_maintenance_recommendation(
    pattern,
    minimum_verified=5
):
    """
    Build a maintenance recommendation only
    when sufficient verified evidence exists.
    """

    requested_pattern = normalize_pattern(
        pattern
    )

    result = build_maintenance_patterns()

    for item in result[
        "patterns"
    ]:

        if item[
            "pattern"
        ] != requested_pattern:
            continue

        verified = item[
            "verified_actions"
        ]

        if verified < minimum_verified:

            return {
                "pattern": requested_pattern,
                "recommendation_status":
                    "INSUFFICIENT EVIDENCE",
                "verified_actions": verified,
                "required_actions":
                    minimum_verified,
                "message": (
                    "Not enough verified maintenance "
                    "outcomes to recommend this action."
                ),
                "evidence_status":
                    item[
                        "evidence_status"
                    ]
            }

        rate = item[
            "improvement_rate"
        ]

        if rate >= 80:

            recommendation_status = (
                "RECOMMENDED"
            )

            message = (
                "Verified maintenance evidence "
                "supports this action pattern."
            )

        elif rate >= 60:

            recommendation_status = (
                "CONDITIONALLY RECOMMENDED"
            )

            message = (
                "Maintenance evidence is moderately "
                "supportive. Human review is required."
            )

        else:

            recommendation_status = (
                "NOT RECOMMENDED"
            )

            message = (
                "Verified outcomes do not provide "
                "strong evidence of effectiveness."
            )

        return {
            "pattern": requested_pattern,
            "recommendation_status":
                recommendation_status,
            "verified_actions": verified,
            "improvement_rate": rate,
            "evidence_status":
                item[
                    "evidence_status"
                ],
            "message": message,
            "supporting_actions":
                item[
                    "actions"
                ]
        }

    return {
        "pattern": requested_pattern,
        "recommendation_status":
            "NO DATA",
        "verified_actions": 0,
        "improvement_rate": 0,
        "evidence_status":
            "NO VERIFIED DATA",
        "message": (
            "No verified maintenance evidence "
            "was found for this pattern."
        ),
        "supporting_actions": []
    }


def build_all_maintenance_recommendations(
    minimum_verified=5
):
    """
    Evaluate every known maintenance pattern.
    """

    patterns = build_maintenance_patterns()

    recommendations = []

    for item in patterns[
        "patterns"
    ]:

        recommendations.append(
            build_maintenance_recommendation(
                item[
                    "pattern"
                ],
                minimum_verified
            )
        )

    return {
        "pattern_count": len(
            recommendations
        ),
        "recommendations":
            recommendations
    }
