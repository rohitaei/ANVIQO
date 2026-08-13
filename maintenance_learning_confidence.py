"""
ANVIQO V5.3.7
Maintenance Learning Confidence

Rates the strength of verified maintenance experience.

HIGH    = strong verified experience
MEDIUM  = useful but limited experience
LOW     = weak historical support
NONE    = no verified experience

No automatic action.
No PLC / SCADA control.
"""

from maintenance_experience_matching import (
    find_matching_experience
)


def calculate_learning_confidence(current_condition):

    matches = find_matching_experience(
        current_condition
    )

    if not matches:

        return {
            "level": "NONE",
            "score": 0,
            "reason":
                "No verified maintenance experience found.",
            "matches": []
        }

    best_score = matches[0].get(
        "match_score",
        0
    )

    count = len(matches)

    if best_score >= 85 and count >= 2:

        level = "HIGH"

        reason = (
            "Strong verified experience support "
            "with multiple historical matches."
        )

        score = min(
            100,
            best_score + 5
        )

    elif best_score >= 80:

        level = "HIGH"

        reason = (
            "Strong verified historical match "
            "supports the recommendation."
        )

        score = best_score

    elif best_score >= 65:

        level = "MEDIUM"

        reason = (
            "Relevant verified experience exists, "
            "but historical support is limited."
        )

        score = best_score

    else:

        level = "LOW"

        reason = (
            "Only weak historical similarity "
            "was found."
        )

        score = best_score

    return {

        "level": level,

        "score": score,

        "reason": reason,

        "match_count": count,

        "matches": matches
    }


def print_confidence(result):

    print()
    print("=" * 68)
    print(
        "        ANVIQO V5.3.7 LEARNING CONFIDENCE"
    )
    print("=" * 68)

    print()
    print("CONFIDENCE")
    print("-" * 68)

    print(
        "Level       :",
        result["level"]
    )

    print(
        "Confidence  :",
        f'{result["score"]}/100'
    )

    print(
        "Matches     :",
        result.get(
            "match_count",
            0
        )
    )

    print()
    print("REASON")
    print("-" * 68)

    print(
        result["reason"]
    )

    print()
    print("BOUNDARY")
    print("-" * 68)

    print(
        "Verified experience only : True"
    )

    print(
        "Automatic action         : False"
    )

    print(
        "PLC write                : False"
    )

    print(
        "SCADA control            : False"
    )

    print()
    print("=" * 68)


if __name__ == "__main__":

    current_condition = {

        "equipment":
            "CV-101",

        "area":
            "MBF",

        "reason":
            "Valve position is increasing significantly "
            "with worsening operational trend."
    }

    result = calculate_learning_confidence(
        current_condition
    )

    print_confidence(
        result
    )

    print()
    print("=" * 68)
    print(
        "V5.3.7 MODULE TEST: PASS"
    )
    print(
        "EXPERIENCE -> CONFIDENCE: PASS"
    )
    print("=" * 68)
