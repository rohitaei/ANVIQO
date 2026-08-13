from maintenance_recommendations import (
    build_maintenance_recommendation
)


def explain_maintenance_recommendation(
    pattern,
    minimum_verified=5
):
    """
    Explain why Anvi recommends, conditionally
    recommends, or refuses to recommend a
    maintenance pattern.
    """

    result = build_maintenance_recommendation(
        pattern,
        minimum_verified
    )

    status = result.get(
        "recommendation_status"
    )

    verified = result.get(
        "verified_actions",
        0
    )

    required = result.get(
        "required_actions",
        minimum_verified
    )

    improvement_rate = result.get(
        "improvement_rate",
        0
    )

    evidence_status = result.get(
        "evidence_status",
        "UNKNOWN"
    )

    if status == "INSUFFICIENT EVIDENCE":

        why = [
            (
                f"Only {verified} verified "
                f"maintenance outcome(s) available."
            ),
            (
                f"At least {required} verified "
                f"outcomes are required."
            ),
            (
                "Current evidence is insufficient "
                "for a maintenance recommendation."
            )
        ]

        conclusion = (
            "Anvi will not recommend this "
            "maintenance pattern yet."
        )

    elif status == "RECOMMENDED":

        why = [
            (
                f"{verified} verified maintenance "
                "outcome(s) are available."
            ),
            (
                f"Observed improvement rate is "
                f"{improvement_rate}%."
            ),
            (
                "The evidence threshold has been "
                "satisfied."
            )
        ]

        conclusion = (
            "Verified evidence supports this "
            "maintenance recommendation."
        )

    elif status == "CONDITIONALLY RECOMMENDED":

        why = [
            (
                f"{verified} verified maintenance "
                "outcome(s) are available."
            ),
            (
                f"Observed improvement rate is "
                f"{improvement_rate}%."
            ),
            (
                "Evidence is supportive but "
                "human review remains required."
            )
        ]

        conclusion = (
            "The maintenance pattern may be useful, "
            "but human review is required."
        )

    elif status == "NOT RECOMMENDED":

        why = [
            (
                f"{verified} verified maintenance "
                "outcome(s) are available."
            ),
            (
                f"Observed improvement rate is "
                f"{improvement_rate}%."
            ),
            (
                "Verified outcomes do not provide "
                "strong evidence of effectiveness."
            )
        ]

        conclusion = (
            "Current verified evidence does not "
            "support this maintenance recommendation."
        )

    else:

        why = [
            "No verified maintenance evidence "
            "is available for this pattern."
        ]

        conclusion = (
            "Anvi cannot make a maintenance "
            "recommendation from the available evidence."
        )

    return {
        "pattern": result.get(
            "pattern"
        ),
        "recommendation_status": status,
        "verified_actions": verified,
        "required_actions": required,
        "improvement_rate": improvement_rate,
        "evidence_status": evidence_status,
        "why": why,
        "conclusion": conclusion
    }
