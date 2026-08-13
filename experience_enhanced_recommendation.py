"""
ANVIQO V5.3.6
Experience-Enhanced Maintenance Recommendation

Combines:
1. Current condition
2. Evidence-backed recommendation
3. Human-verified historical experience

No automatic action.
No PLC / SCADA control.
"""

from maintenance_experience_matching import (
    build_experience_context
)


def build_enhanced_recommendation(
    current_condition,
    base_recommendation
):

    experience = build_experience_context(
        current_condition
    )

    result = {

        "version": "V5.3.6",

        "equipment":
            current_condition.get(
                "equipment",
                "UNKNOWN"
            ),

        "area":
            current_condition.get(
                "area",
                "UNKNOWN"
            ),

        "priority":
            base_recommendation.get(
                "priority",
                0
            ),

        "base_recommendation":
            base_recommendation.get(
                "recommendation",
                ""
            ),

        "experience_found":
            experience.get(
                "experience_found",
                False
            ),

        "experience_context":
            experience,

        "human_verification_required":
            True,

        "automatic_action":
            False,

        "control_boundary": {

            "read_only": True,

            "plc_write": False,

            "scada_control": False
        }
    }

    if experience.get(
        "experience_found"
    ):

        best = experience[
            "best_match"
        ]

        result[
            "enhanced_recommendation"
        ] = (
            base_recommendation.get(
                "recommendation",
                ""
            )
            + " A similar verified condition "
            "was previously managed on "
            f'{best["equipment"]}. '
            "The previous maintenance action "
            f'was: {best["previous_action"]} '
            f'and the verified outcome was '
            f'{best["previous_outcome"]}.'
        )

        result[
            "experience_confidence"
        ] = best[
            "match_score"
        ]

    else:

        result[
            "enhanced_recommendation"
        ] = (
            base_recommendation.get(
                "recommendation",
                ""
            )
            + " No sufficiently similar "
            "verified maintenance experience "
            "was found."
        )

        result[
            "experience_confidence"
        ] = 0

    return result


def print_result(
    result
):

    print()
    print("=" * 68)
    print(
        "        ANVIQO V5.3.6 EXPERIENCE-ENHANCED RECOMMENDATION"
    )
    print("=" * 68)

    print()
    print("EQUIPMENT")
    print("-" * 68)

    print(
        f'{result["equipment"]} | '
        f'{result["area"]}'
    )

    print()
    print("PRIORITY")
    print("-" * 68)

    print(
        f'{result["priority"]}/100'
    )

    print()
    print("BASE RECOMMENDATION")
    print("-" * 68)

    print(
        result["base_recommendation"]
    )

    print()
    print("EXPERIENCE MATCH")
    print("-" * 68)

    print(
        "Verified experience found :",
        result["experience_found"]
    )

    print(
        "Experience confidence      :",
        f'{result["experience_confidence"]}/100'
    )

    print()
    print("ENHANCED RECOMMENDATION")
    print("-" * 68)

    print(
        result["enhanced_recommendation"]
    )

    print()
    print("HUMAN VERIFICATION")
    print("-" * 68)

    print(
        "Required        :",
        result["human_verification_required"]
    )

    print(
        "Automatic action:",
        result["automatic_action"]
    )

    print()
    print("CONTROL BOUNDARY")
    print("-" * 68)

    control = result[
        "control_boundary"
    ]

    print(
        "Read-only :",
        control["read_only"]
    )

    print(
        "PLC write :",
        control["plc_write"]
    )

    print(
        "SCADA     :",
        control["scada_control"]
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

    base_recommendation = {

        "priority":
            84.7,

        "recommendation":
            "Perform a controlled maintenance review "
            "of the equipment and verify the associated "
            "process condition."
    }

    result = build_enhanced_recommendation(

        current_condition,

        base_recommendation
    )

    print_result(
        result
    )

    print()
    print("=" * 68)
    print(
        "V5.3.6 MODULE TEST: PASS"
    )
    print(
        "EVIDENCE -> EXPERIENCE -> RECOMMENDATION: PASS"
    )
    print("=" * 68)
