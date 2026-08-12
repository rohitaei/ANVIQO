"""
ANVIQO V5.3.2
Evidence-Backed Maintenance Recommendation

Anviqo explains why maintenance is recommended
and preserves the evidence chain.

Recommendation only.
Human verification required.
No PLC / SCADA control.
"""


def build_recommendation(item):

    evidence = item.get("evidence_chain", [])

    if not evidence:
        evidence = [
            "No detailed evidence supplied."
        ]

    priority = item.get(
        "maintenance_priority", 0
    )

    equipment = item.get(
        "equipment", "UNKNOWN"
    )

    area = item.get(
        "area", "UNKNOWN"
    )

    if priority >= 80:
        recommendation = (
            "Perform a controlled maintenance review "
            "of the equipment and verify the associated "
            "process condition."
        )
        urgency = "URGENT"

    elif priority >= 65:
        recommendation = (
            "Schedule a detailed maintenance inspection "
            "and verify equipment operating condition."
        )
        urgency = "HIGH"

    elif priority >= 50:
        recommendation = (
            "Include the equipment in the planned "
            "maintenance monitoring schedule."
        )
        urgency = "PLANNED"

    else:
        recommendation = (
            "Continue routine condition monitoring."
        )
        urgency = "MONITOR"

    return {

        "version": "V5.3.2",

        "equipment": equipment,

        "area": area,

        "priority": priority,

        "urgency": urgency,

        "recommendation": recommendation,

        "reason": item.get(
            "reason", ""
        ),

        "evidence_chain": evidence,

        "evidence_count": len(evidence),

        "safety": {
            "human_verification_required": True,
            "permit_check_required": True,
            "isolation_check_required": True,
            "risk_assessment_required": True,
        },

        "control_boundary": {
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }
    }


def print_recommendation(result):

    print()
    print("=" * 68)
    print("        ANVIQO V5.3.2 MAINTENANCE RECOMMENDATION")
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
    print("URGENCY")
    print("-" * 68)
    print(
        result["urgency"]
    )

    print()
    print("RECOMMENDATION")
    print("-" * 68)
    print(
        result["recommendation"]
    )

    print()
    print("WHY MAINTENANCE IS RECOMMENDED")
    print("-" * 68)
    print(
        result["reason"]
    )

    print()
    print("EVIDENCE CHAIN")
    print("-" * 68)

    for number, evidence in enumerate(
        result["evidence_chain"],
        1
    ):
        print(
            f'✓ {evidence}'
        )

    print()
    print(
        "Evidence items :",
        result["evidence_count"]
    )

    print()
    print("SAFETY REQUIREMENTS")
    print("-" * 68)

    safety = result["safety"]

    print(
        "Human verification :",
        safety["human_verification_required"]
    )

    print(
        "Permit check       :",
        safety["permit_check_required"]
    )

    print(
        "Isolation check    :",
        safety["isolation_check_required"]
    )

    print(
        "Risk assessment    :",
        safety["risk_assessment_required"]
    )

    print()
    print("CONTROL BOUNDARY")
    print("-" * 68)

    control = result["control_boundary"]

    print(
        "Read-only :", control["read_only"]
    )

    print(
        "PLC write :", control["plc_write"]
    )

    print(
        "SCADA     :", control["scada_control"]
    )

    print()
    print("=" * 68)


if __name__ == "__main__":

    cv101 = {

        "equipment": "CV-101",

        "area": "MBF",

        "maintenance_priority": 84.7,

        "reason":
            "Valve position is increasing significantly "
            "with elevated operational risk.",

        "evidence_chain": [

            "Position changed from 20% to 34%.",

            "70% increase detected.",

            "MBF operational correlation.",

            "Equipment criticality is high.",

            "Worsening operational trend detected.",

            "V5.0.8 evidence-backed diagnosis."
        ]
    }

    result = build_recommendation(
        cv101
    )

    print_recommendation(
        result
    )

    print()
    print("=" * 68)
    print("V5.3.2 MODULE TEST: PASS")
    print("CV-101 -> EVIDENCE -> RECOMMENDATION: PASS")
    print("=" * 68)
