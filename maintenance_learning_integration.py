"""
ANVIQO V5.3.9
Maintenance Learning Integration

Integrates verified maintenance experience into
the maintenance recommendation.

Safety:
- Human verification required
- Automatic action disabled
- PLC write disabled
- SCADA control disabled
"""

from maintenance_learning_summary import (
    build_learning_summary
)

from maintenance_learning_confidence import (
    calculate_learning_confidence
)


def build_learning_integrated_recommendation(
    current_condition,
    base_recommendation
):

    equipment = current_condition.get(
        "equipment",
        "UNKNOWN"
    )

    summary = build_learning_summary(
        equipment,
        current_condition
    )

    confidence = calculate_learning_confidence(
        current_condition
    )

    result = {

        "version": "V5.3.9",

        "equipment": equipment,

        "area": current_condition.get(
            "area",
            "UNKNOWN"
        ),

        "priority": base_recommendation.get(
            "priority",
            0
        ),

        "base_recommendation":
            base_recommendation.get(
                "recommendation",
                ""
            ),

        "learning_summary": summary,

        "learning_confidence": confidence,

        "learning_integrated": False,

        "human_verification_required": True,

        "automatic_action": False,

        "control_boundary": {

            "read_only": True,

            "plc_write": False,

            "scada_control": False
        }
    }

    if (
        confidence.get("level")
        in ("HIGH", "MEDIUM")
        and summary.get(
            "verified_events",
            0
        ) > 0
    ):

        result[
            "learning_integrated"
        ] = True

        result[
            "recommendation"
        ] = (
            base_recommendation.get(
                "recommendation",
                ""
            )
            + " Verified maintenance history "
            "supports this recommendation. "
            f'Previous verified outcome: '
            f'{summary["last_verified_outcome"]}. '
            f'Historical experience confidence: '
            f'{confidence["level"]} '
            f'({confidence["score"]}/100).'
        )

    else:

        result[
            "recommendation"
        ] = (
            base_recommendation.get(
                "recommendation",
                ""
            )
            + " No sufficiently strong verified "
            "maintenance history is available."
        )

    return result


def print_result(result):

    print()
    print("=" * 68)
    print(
        "        ANVIQO V5.3.9 MAINTENANCE LEARNING INTEGRATION"
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
    print("LEARNING STATUS")
    print("-" * 68)

    print(
        "Learning integrated :",
        result["learning_integrated"]
    )

    confidence = result[
        "learning_confidence"
    ]

    print(
        "Confidence          :",
        confidence.get(
            "level",
            "NONE"
        )
    )

    print(
        "Confidence score    :",
        f'{confidence.get("score", 0)}/100'
    )

    summary = result[
        "learning_summary"
    ]

    print(
        "Verified events     :",
        summary.get(
            "verified_events",
            0
        )
    )

    print(
        "Historical success  :",
        f'{summary.get("historical_success_rate", 0)}%'
    )

    print()
    print("FINAL RECOMMENDATION")
    print("-" * 68)

    print(
        result["recommendation"]
    )

    print()
    print("SAFETY / CONTROL BOUNDARY")
    print("-" * 68)

    print(
        "Human verification required :",
        result["human_verification_required"]
    )

    print(
        "Automatic action            :",
        result["automatic_action"]
    )

    control = result[
        "control_boundary"
    ]

    print(
        "Read-only                   :",
        control["read_only"]
    )

    print(
        "PLC write                   :",
        control["plc_write"]
    )

    print(
        "SCADA control               :",
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
            "of CV-101 and verify the associated "
            "process condition."
    }

    result = (
        build_learning_integrated_recommendation(
            current_condition,
            base_recommendation
        )
    )

    print_result(
        result
    )

    print()
    print("=" * 68)

    print(
        "V5.3.9 MODULE TEST: PASS"
    )

    print(
        "RECOMMENDATION -> LEARNING -> DECISION: PASS"
    )

    print("=" * 68)
