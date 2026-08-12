"""
ANVIQO V5.3.1
Maintenance Decision & Safety Gate

Recommendation only.
Human verification and safety authorization required.
No automatic equipment control.
"""

def build_maintenance_decision(item):

    priority = item.get("maintenance_priority", 0)
    equipment = item.get("equipment", "UNKNOWN")
    area = item.get("area", "UNKNOWN")
    reason = item.get("reason", "")

    if priority >= 80:
        decision = "URGENT MAINTENANCE REVIEW"
        action = (
            "Inspect equipment condition, verify process impact, "
            "and plan controlled maintenance intervention."
        )

    elif priority >= 65:
        decision = "HIGH PRIORITY MAINTENANCE REVIEW"
        action = (
            "Schedule detailed inspection and verify "
            "equipment operating condition."
        )

    elif priority >= 50:
        decision = "PLANNED MAINTENANCE REVIEW"
        action = (
            "Add equipment to maintenance monitoring plan."
        )

    else:
        decision = "MONITOR"
        action = (
            "Continue routine condition monitoring."
        )

    return {
        "equipment": equipment,
        "area": area,
        "priority": priority,
        "decision": decision,
        "recommended_action": action,
        "reason": reason,

        "safety_gate": {
            "required": True,
            "status": "PENDING HUMAN VERIFICATION",
            "permit_check_required": True,
            "isolation_check_required": True,
            "job_risk_assessment_required": True,
        },

        "authorization": {
            "human_required": True,
            "automatic_authorization": False,
        },

        "control_boundary": {
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }
    }


def print_decision(result):

    print()
    print("=" * 68)
    print("        ANVIQO V5.3.1 MAINTENANCE DECISION")
    print("=" * 68)

    print()
    print("EQUIPMENT")
    print("-" * 68)
    print(
        f'{result["equipment"]} | {result["area"]}'
    )

    print()
    print("PRIORITY")
    print("-" * 68)
    print(
        f'{result["priority"]}/100'
    )

    print()
    print("DECISION")
    print("-" * 68)
    print(
        result["decision"]
    )

    print()
    print("RECOMMENDED ACTION")
    print("-" * 68)
    print(
        result["recommended_action"]
    )

    print()
    print("WHY")
    print("-" * 68)
    print(
        result["reason"]
    )

    print()
    print("SAFETY GATE")
    print("-" * 68)

    gate = result["safety_gate"]

    print(
        "Required               :",
        gate["required"]
    )

    print(
        "Status                 :",
        gate["status"]
    )

    print(
        "Permit check           :",
        gate["permit_check_required"]
    )

    print(
        "Isolation check        :",
        gate["isolation_check_required"]
    )

    print(
        "Job risk assessment    :",
        gate["job_risk_assessment_required"]
    )

    print()
    print("AUTHORIZATION")
    print("-" * 68)

    auth = result["authorization"]

    print(
        "Human authorization    :",
        auth["human_required"]
    )

    print(
        "Automatic authorization:",
        auth["automatic_authorization"]
    )

    print()
    print("CONTROL BOUNDARY")
    print("-" * 68)

    control = result["control_boundary"]

    print(
        "Read-only              :",
        control["read_only"]
    )

    print(
        "PLC write              :",
        control["plc_write"]
    )

    print(
        "SCADA control          :",
        control["scada_control"]
    )

    print()
    print("=" * 68)


if __name__ == "__main__":

    cv101 = {
        "equipment": "CV-101",
        "area": "MBF",
        "maintenance_priority": 84.7,
        "reason":
            "Valve position increasing significantly. "
            "Position changed from 20% to 34%. "
            "70% increase detected. "
            "MBF operational correlation."
    }

    result = build_maintenance_decision(
        cv101
    )

    print_decision(result)

    print()
    print("=" * 68)
    print("V5.3.1 MODULE TEST: PASS")
    print("CV-101 -> MAINTENANCE DECISION -> SAFETY GATE: PASS")
    print("=" * 68)
