"""
ANVIQO V5.3.10
Maintenance Decision Explanation

Explains WHY Anviqo recommends maintenance by combining:
- Current evidence
- Operational priority
- Verified maintenance history
- Learning confidence
- Safety requirements

No automatic action.
No PLC / SCADA control.
"""

from maintenance_learning_integration import (
    build_learning_integrated_recommendation
)


def build_decision_explanation(
    current_condition,
    base_recommendation
):

    decision = build_learning_integrated_recommendation(
        current_condition,
        base_recommendation
    )

    summary = decision[
        "learning_summary"
    ]

    confidence = decision[
        "learning_confidence"
    ]

    reasons = []

    # Current operational evidence
    reason = current_condition.get(
        "reason",
        ""
    )

    if reason:
        reasons.append(
            "Current evidence: " + reason
        )

    # Priority
    priority = decision.get(
        "priority",
        0
    )

    if priority >= 80:
        reasons.append(
            f"High operational priority detected ({priority}/100)."
        )
    elif priority >= 60:
        reasons.append(
            f"Moderate operational priority detected ({priority}/100)."
        )

    # Historical experience
    if decision.get(
        "learning_integrated",
        False
    ):

        reasons.append(
            "Verified maintenance history supports "
            "the recommended intervention."
        )

        previous_outcome = summary.get(
            "last_verified_outcome",
            "UNKNOWN"
        )

        reasons.append(
            "Previous verified maintenance outcome: "
            + previous_outcome
            + "."
        )

        reasons.append(
            "Historical experience confidence: "
            + confidence.get(
                "level",
                "NONE"
            )
            + " ("
            + str(
                confidence.get(
                    "score",
                    0
                )
            )
            + "/100)."
        )

    else:

        reasons.append(
            "No sufficiently strong verified "
            "maintenance history was available."
        )

    explanation = {

        "version": "V5.3.10",

        "equipment":
            decision["equipment"],

        "area":
            decision["area"],

        "priority":
            priority,

        "recommendation":
            decision["recommendation"],

        "why":
            reasons,

        "learning_supported":
            decision[
                "learning_integrated"
            ],

        "learning_confidence":
            confidence.get(
                "level",
                "NONE"
            ),

        "learning_confidence_score":
            confidence.get(
                "score",
                0
            ),

        "human_verification_required":
            True,

        "automatic_action":
            False,

        "safety_gate": {

            "human_verification":
                True,

            "permit_check":
                True,

            "isolation_check":
                True,

            "risk_assessment":
                True
        },

        "control_boundary": {

            "read_only":
                True,

            "plc_write":
                False,

            "scada_control":
                False
        }
    }

    return explanation


def print_explanation(
    result
):

    print()
    print("=" * 68)
    print(
        "        ANVIQO V5.3.10 MAINTENANCE DECISION EXPLANATION"
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
    print("WHY MAINTENANCE IS RECOMMENDED")
    print("-" * 68)

    for reason in result["why"]:

        print(
            "✓",
            reason
        )

    print()
    print("RECOMMENDATION")
    print("-" * 68)

    print(
        result["recommendation"]
    )

    print()
    print("LEARNING SUPPORT")
    print("-" * 68)

    print(
        "Learning supported :",
        result["learning_supported"]
    )

    print(
        "Confidence          :",
        result["learning_confidence"]
    )

    print(
        "Confidence score    :",
        f'{result["learning_confidence_score"]}/100'
    )

    print()
    print("SAFETY GATE")
    print("-" * 68)

    safety = result[
        "safety_gate"
    ]

    print(
        "Human verification :",
        safety["human_verification"]
    )

    print(
        "Permit check       :",
        safety["permit_check"]
    )

    print(
        "Isolation check    :",
        safety["isolation_check"]
    )

    print(
        "Risk assessment    :",
        safety["risk_assessment"]
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
            "of CV-101 and verify the associated "
            "process condition."
    }

    result = build_decision_explanation(
        current_condition,
        base_recommendation
    )

    print_explanation(
        result
    )

    print()
    print("=" * 68)

    print(
        "V5.3.10 MODULE TEST: PASS"
    )

    print(
        "EVIDENCE -> LEARNING -> EXPLANATION: PASS"
    )

    print("=" * 68)
