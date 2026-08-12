import json
import os

from learning_aggregation import (
    aggregate_learning_evidence
)

from pattern_context import (
    match_pattern_context
)


MINIMUM_VERIFIED_ACTIONS = 5


def decide_recommendation(
    equipment,
    current_pattern
):
    """
    Decide whether a maintenance recommendation
    has enough verified evidence to proceed.

    This function NEVER approves or executes
    maintenance. Human approval remains mandatory.
    """

    context = match_pattern_context(
        equipment=equipment,
        current_pattern=current_pattern
    )

    aggregation = aggregate_learning_evidence(
        equipment=equipment
    )

    verified_actions = aggregation.get(
        "verified_actions",
        0
    )

    evidence_strength = aggregation.get(
        "evidence_strength",
        "INSUFFICIENT DATA"
    )

    reasons = []

    if not context.get(
        "matched",
        False
    ):
        reasons.append(
            "Current equipment and maintenance "
            "pattern do not match verified "
            "historical evidence."
        )

    if verified_actions < MINIMUM_VERIFIED_ACTIONS:
        reasons.append(
            f"Only {verified_actions} verified "
            f"maintenance outcome(s) available. "
            f"At least {MINIMUM_VERIFIED_ACTIONS} "
            "are required."
        )

    if evidence_strength != "STRONG":
        reasons.append(
            "Verified evidence strength is not STRONG."
        )

    if (
        context.get("matched", False)
        and verified_actions >= MINIMUM_VERIFIED_ACTIONS
        and evidence_strength == "STRONG"
    ):
        recommendation_status = "RECOMMENDED"

        reason = (
            "Current condition matches the "
            "historical pattern and the verified "
            "evidence threshold has been satisfied."
        )

    else:
        recommendation_status = (
            "INSUFFICIENT EVIDENCE"
        )

        reason = (
            "Recommendation cannot proceed "
            "because the verified evidence "
            "requirements have not been satisfied."
        )

    return {
        "equipment":
            equipment,
        "current_pattern":
            current_pattern,
        "recommendation_status":
            recommendation_status,
        "evidence_strength":
            evidence_strength,
        "verified_actions":
            verified_actions,
        "required_actions":
            MINIMUM_VERIFIED_ACTIONS,
        "context":
            context,
        "reasons":
            reasons,
        "reason":
            reason,
        "human_approval_required":
            True
    }
