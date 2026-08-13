from maintenance_recommendations import (
    build_maintenance_recommendation
)

from maintenance_context import (
    match_maintenance_context
)


def build_context_aware_recommendation(
    equipment,
    current_evidence=None,
    possible_causes=None,
    historical_pattern=None,
    minimum_verified=5
):
    """
    Combine current condition context with
    verified maintenance evidence.
    """

    context = match_maintenance_context(
        current_evidence=current_evidence,
        possible_causes=possible_causes,
        equipment=equipment,
        historical_pattern=historical_pattern
    )

    recommendation = (
        build_maintenance_recommendation(
            historical_pattern,
            minimum_verified
        )
    )

    if not context.get(
        "matched"
    ):

        return {
            "equipment": equipment,
            "historical_pattern":
                historical_pattern,
            "context_status":
                "NO MATCH",
            "recommendation_status":
                "NOT RECOMMENDED",
            "reason": (
                "Current equipment condition does "
                "not match the historical pattern."
            ),
            "context": context,
            "recommendation":
                recommendation
        }

    if recommendation.get(
        "recommendation_status"
    ) == "INSUFFICIENT EVIDENCE":

        return {
            "equipment": equipment,
            "historical_pattern":
                historical_pattern,
            "context_status":
                "MATCH",
            "recommendation_status":
                "INSUFFICIENT EVIDENCE",
            "reason": (
                "Current condition matches the "
                "historical pattern, but there is "
                "not enough verified maintenance "
                "evidence to recommend the action."
            ),
            "context": context,
            "recommendation":
                recommendation
        }

    return {
        "equipment": equipment,
        "historical_pattern":
            historical_pattern,
        "context_status":
            "MATCH",
        "recommendation_status":
            recommendation.get(
                "recommendation_status"
            ),
        "reason":
            recommendation.get(
                "message"
            ),
        "context": context,
        "recommendation":
            recommendation
    }
