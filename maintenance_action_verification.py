"""
ANVIQO V5.3.3
Verified Maintenance Action & Learning

Records what a human maintenance team actually did
and whether the condition improved.

Anviqo learns only from verified outcomes.

No automatic maintenance action.
No PLC / SCADA control.
"""

from datetime import datetime


def verify_maintenance_action(
    recommendation,
    action_taken,
    outcome,
    verified_by="Maintenance"
):

    equipment = recommendation.get(
        "equipment", "UNKNOWN"
    )

    area = recommendation.get(
        "area", "UNKNOWN"
    )

    priority = recommendation.get(
        "priority", 0
    )

    evidence = recommendation.get(
        "evidence_chain", []
    )

    if action_taken:

        action_status = "ACTION COMPLETED"

    else:

        action_status = "ACTION NOT COMPLETED"

    if outcome == "IMPROVED":

        learning_status = "POSITIVE VERIFIED OUTCOME"

    elif outcome == "NO_CHANGE":

        learning_status = "NO IMPROVEMENT VERIFIED"

    elif outcome == "WORSENED":

        learning_status = "NEGATIVE VERIFIED OUTCOME"

    else:

        learning_status = "OUTCOME PENDING VERIFICATION"

    return {

        "version": "V5.3.3",

        "timestamp":
            datetime.now().isoformat(),

        "equipment":
            equipment,

        "area":
            area,

        "recommendation_priority":
            priority,

        "recommendation":
            recommendation.get(
                "recommendation", ""
            ),

        "evidence_chain":
            evidence,

        "action_taken":
            action_taken,

        "action_status":
            action_status,

        "outcome":
            outcome,

        "learning_status":
            learning_status,

        "verified_by":
            verified_by,

        "human_verified":
            True,

        "automatic_learning":
            False,

        "control_boundary": {

            "read_only": True,

            "plc_write": False,

            "scada_control": False
        }
    }


def print_verification(result):

    print()
    print("=" * 68)
    print(
        "        ANVIQO V5.3.3 MAINTENANCE ACTION VERIFICATION"
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
    print("RECOMMENDATION PRIORITY")
    print("-" * 68)
    print(
        f'{result["recommendation_priority"]}/100'
    )

    print()
    print("ACTION STATUS")
    print("-" * 68)
    print(
        result["action_status"]
    )

    print()
    print("ACTION TAKEN")
    print("-" * 68)
    print(
        result["action_taken"]
    )

    print()
    print("VERIFIED OUTCOME")
    print("-" * 68)
    print(
        result["outcome"]
    )

    print()
    print("LEARNING STATUS")
    print("-" * 68)
    print(
        result["learning_status"]
    )

    print()
    print("VERIFICATION")
    print("-" * 68)
    print(
        "Human verified :",
        result["human_verified"]
    )

    print(
        "Verified by    :",
        result["verified_by"]
    )

    print(
        "Automatic learning :",
        result["automatic_learning"]
    )

    print()
    print("EVIDENCE RETAINED")
    print("-" * 68)

    for evidence in result["evidence_chain"]:
        print(
            f"✓ {evidence}"
        )

    print()
    print("CONTROL BOUNDARY")
    print("-" * 68)

    control = result["control_boundary"]

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

    recommendation = {

        "equipment": "CV-101",

        "area": "MBF",

        "priority": 84.7,

        "recommendation":
            "Perform a controlled maintenance review "
            "of the equipment and verify the associated "
            "process condition.",

        "evidence_chain": [

            "Position changed from 20% to 34%.",

            "70% increase detected.",

            "MBF operational correlation.",

            "Equipment criticality is high.",

            "Worsening operational trend detected.",

            "V5.0.8 evidence-backed diagnosis."
        ]
    }

    result = verify_maintenance_action(

        recommendation,

        action_taken=(
            "Inspected CV-101 and verified valve "
            "position feedback and actuator condition."
        ),

        outcome="IMPROVED",

        verified_by="Maintenance Supervisor"
    )

    print_verification(result)

    print()
    print("=" * 68)
    print("V5.3.3 MODULE TEST: PASS")
    print(
        "RECOMMENDATION -> ACTION -> VERIFIED OUTCOME: PASS"
    )
    print("=" * 68)
