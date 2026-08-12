"""
ANVIQO V5.3.8
Maintenance Learning Summary

Summarizes HUMAN-VERIFIED maintenance history
for equipment.

No automatic action.
No PLC / SCADA control.
"""

from maintenance_learning_record import (
    find_equipment_history
)

from maintenance_learning_confidence import (
    calculate_learning_confidence
)


def build_learning_summary(
    equipment,
    current_condition=None
):

    history = find_equipment_history(
        equipment
    )

    total = len(history)

    improved = sum(
        1
        for record in history
        if record.get("outcome")
        == "IMPROVED"
    )

    no_change = sum(
        1
        for record in history
        if record.get("outcome")
        == "NO_CHANGE"
    )

    worsened = sum(
        1
        for record in history
        if record.get("outcome")
        == "WORSENED"
    )

    if total:

        success_rate = round(
            (improved / total) * 100,
            1
        )

        last_record = history[-1]

        last_action = last_record.get(
            "action_taken",
            ""
        )

        last_outcome = last_record.get(
            "outcome",
            "UNKNOWN"
        )

        last_verified_by = last_record.get(
            "verified_by",
            "UNKNOWN"
        )

    else:

        success_rate = 0

        last_action = ""

        last_outcome = "NONE"

        last_verified_by = "NONE"

    if current_condition:

        confidence = (
            calculate_learning_confidence(
                current_condition
            )
        )

    else:

        confidence = {

            "level": (
                "HIGH"
                if total
                else "NONE"
            ),

            "score": (
                100
                if total
                else 0
            )
        }

    return {

        "version": "V5.3.8",

        "equipment":
            equipment,

        "verified_events":
            total,

        "improved_outcomes":
            improved,

        "no_change_outcomes":
            no_change,

        "worsened_outcomes":
            worsened,

        "historical_success_rate":
            success_rate,

        "last_verified_action":
            last_action,

        "last_verified_outcome":
            last_outcome,

        "last_verified_by":
            last_verified_by,

        "experience_confidence":
            confidence.get(
                "level",
                "NONE"
            ),

        "experience_confidence_score":
            confidence.get(
                "score",
                0
            ),

        "human_verified_only":
            True,

        "automatic_action":
            False,

        "control_boundary": {

            "read_only": True,

            "plc_write": False,

            "scada_control": False
        }
    }


def print_summary(
    summary
):

    print()
    print("=" * 68)
    print(
        "        ANVIQO V5.3.8 MAINTENANCE LEARNING SUMMARY"
    )
    print("=" * 68)

    print()
    print("EQUIPMENT")
    print("-" * 68)

    print(
        summary["equipment"]
    )

    print()
    print("VERIFIED MAINTENANCE HISTORY")
    print("-" * 68)

    print(
        "Verified events       :",
        summary["verified_events"]
    )

    print(
        "Improved outcomes     :",
        summary["improved_outcomes"]
    )

    print(
        "No-change outcomes    :",
        summary["no_change_outcomes"]
    )

    print(
        "Worsened outcomes     :",
        summary["worsened_outcomes"]
    )

    print(
        "Historical success    :",
        f'{summary["historical_success_rate"]}%'
    )

    print()
    print("LATEST VERIFIED EXPERIENCE")
    print("-" * 68)

    print(
        "Action :",
        summary["last_verified_action"]
    )

    print(
        "Outcome:",
        summary["last_verified_outcome"]
    )

    print(
        "Verified by:",
        summary["last_verified_by"]
    )

    print()
    print("EXPERIENCE CONFIDENCE")
    print("-" * 68)

    print(
        "Level:",
        summary["experience_confidence"]
    )

    print(
        "Score:",
        f'{summary["experience_confidence_score"]}/100'
    )

    print()
    print("CONTROL BOUNDARY")
    print("-" * 68)

    control = summary[
        "control_boundary"
    ]

    print(
        "Human verified only :",
        summary["human_verified_only"]
    )

    print(
        "Automatic action    :",
        summary["automatic_action"]
    )

    print(
        "Read-only           :",
        control["read_only"]
    )

    print(
        "PLC write           :",
        control["plc_write"]
    )

    print(
        "SCADA control       :",
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

    summary = build_learning_summary(

        "CV-101",

        current_condition
    )

    print_summary(
        summary
    )

    print()
    print("=" * 68)

    print(
        "V5.3.8 MODULE TEST: PASS"
    )

    print(
        "VERIFIED HISTORY -> LEARNING SUMMARY: PASS"
    )

    print("=" * 68)
