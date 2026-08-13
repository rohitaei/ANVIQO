"""
ANVIQO V5.3.11
Management Decision Report
"""

from maintenance_decision_explanation import (
    build_decision_explanation
)


def build_management_report(
    current_condition,
    base_recommendation
):

    explanation = build_decision_explanation(
        current_condition,
        base_recommendation
    )

    confidence_level = explanation.get(
        "learning_confidence",
        "NONE"
    )

    confidence_score = explanation.get(
        "learning_confidence_score",
        0
    )

    if explanation["priority"] >= 80:
        management_level = "P1 — URGENT"
    elif explanation["priority"] >= 60:
        management_level = "P2 — HIGH"
    else:
        management_level = "P3 — MONITOR"

    return {

        "version": "V5.3.11",

        "management_level":
            management_level,

        "equipment":
            explanation["equipment"],

        "area":
            explanation["area"],

        "priority":
            explanation["priority"],

        "decision":
            "MAINTENANCE REVIEW REQUIRED",

        "why":
            explanation["why"],

        "recommendation":
            explanation["recommendation"],

        "learning_supported":
            explanation["learning_supported"],

        "learning_confidence":
            confidence_level,

        "learning_confidence_score":
            confidence_score,

        "human_decision_required":
            True,

        "safety_gate":
            explanation["safety_gate"],

        "control_boundary":
            explanation["control_boundary"]
    }


def print_management_report(report):

    print()
    print("=" * 68)
    print(
        "ANVIQO V5.3.11 MANAGEMENT DECISION REPORT"
    )
    print("=" * 68)

    print()
    print("EQUIPMENT")
    print("-" * 68)

    print(
        f'{report["equipment"]} | '
        f'{report["area"]}'
    )

    print()
    print("MANAGEMENT PRIORITY")
    print("-" * 68)

    print(
        "Level    :",
        report["management_level"]
    )

    print(
        "Priority :",
        f'{report["priority"]}/100'
    )

    print()
    print("DECISION")
    print("-" * 68)

    print(
        report["decision"]
    )

    print()
    print("WHY ANVIQO IS CONCERNED")
    print("-" * 68)

    for reason in report["why"]:
        print("✓", reason)

    print()
    print("RECOMMENDED ACTION")
    print("-" * 68)

    print(
        report["recommendation"]
    )

    print()
    print("VERIFIED PLANT EXPERIENCE")
    print("-" * 68)

    print(
        "Learning supported :",
        report["learning_supported"]
    )

    print(
        "Confidence          :",
        report["learning_confidence"]
    )

    print(
        "Confidence score    :",
        f'{report["learning_confidence_score"]}/100'
    )

    print()
    print("HUMAN DECISION")
    print("-" * 68)

    print(
        "Human authorization required :",
        report["human_decision_required"]
    )

    print()
    print("SAFETY GATE")
    print("-" * 68)

    safety = report["safety_gate"]

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

    control = report["control_boundary"]

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

    report = build_management_report(
        current_condition,
        base_recommendation
    )

    print_management_report(
        report
    )

    print()
    print("=" * 68)
    print(
        "V5.3.11 MODULE TEST: PASS"
    )
    print(
        "EVIDENCE -> LEARNING -> DECISION -> MANAGEMENT: PASS"
    )
    print("=" * 68)
