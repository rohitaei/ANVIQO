"""
ANVIQO V5.3.0
Maintenance Priority Intelligence

Converts operational conditions into a ranked
maintenance priority queue.

Anviqo recommends.
Human verifies and authorizes.

Read-only prototype.
No PLC / WinCC / SCADA control.
"""


def calculate_maintenance_priority(item):

    risk = item.get("risk", 0)
    criticality = item.get("criticality", 0)
    trend = item.get("trend", 0)
    evidence = item.get("evidence", 0)

    priority = round(
        risk * 0.35
        + criticality * 0.30
        + trend * 0.20
        + evidence * 0.15,
        1
    )

    return priority


def maintenance_level(priority):

    if priority >= 80:
        return "P1 — URGENT"

    if priority >= 65:
        return "P2 — HIGH"

    if priority >= 50:
        return "P3 — PLANNED"

    return "P4 — MONITOR"


def build_maintenance_priority(plant_status):

    ranking = (
        plant_status
        .get("priority_engine", {})
        .get("ranking", [])
    )

    maintenance_queue = []

    for item in ranking:

        priority = calculate_maintenance_priority(
            item
        )

        level = maintenance_level(
            priority
        )

        severity = item.get(
            "severity", "NORMAL"
        )

        if priority >= 80:

            action = (
                "Maintenance review required. "
                "Verify equipment condition and "
                "associated process behaviour."
            )

        elif priority >= 65:

            action = (
                "Maintenance inspection recommended "
                "during controlled opportunity."
            )

        elif priority >= 50:

            action = (
                "Add to maintenance monitoring plan."
            )

        else:

            action = (
                "Continue routine monitoring."
            )

        maintenance_queue.append({

            "equipment":
                item.get("equipment", "UNKNOWN"),

            "area":
                item.get("area", "UNKNOWN"),

            "maintenance_priority":
                priority,

            "maintenance_level":
                level,

            "operational_severity":
                severity,

            "recommended_action":
                action,

            "reason":
                item.get("reason", ""),

            "evidence_chain":
                item.get("evidence_chain", []),

            "human_verification_required":
                True,

            "automatic_action":
                False,
        })

    maintenance_queue.sort(
        key=lambda x:
            x["maintenance_priority"],
        reverse=True
    )

    for position, item in enumerate(
        maintenance_queue,
        1
    ):
        item["queue_position"] = position

    return {

        "version": "V5.3.0",

        "maintenance_count":
            len(maintenance_queue),

        "maintenance_queue":
            maintenance_queue,

        "decision_mode":
            "RECOMMENDATION ONLY",

        "human_verification_required":
            True,

        "automatic_action":
            False,

        "read_only":
            True,

        "scada_control":
            False,
    }


def print_maintenance_priority(result):

    print()
    print("=" * 68)
    print("        ANVIQO V5.3.0 MAINTENANCE PRIORITY")
    print("=" * 68)

    print()
    print("DECISION MODE")
    print("-" * 68)
    print(result["decision_mode"])

    print()
    print("MAINTENANCE QUEUE")
    print("-" * 68)

    if not result["maintenance_queue"]:

        print("No maintenance priorities identified.")

    for item in result["maintenance_queue"]:

        print()
        print(
            f'{item["queue_position"]}. '
            f'{item["equipment"]} | '
            f'{item["area"]}'
        )

        print(
            f'   Priority : '
            f'{item["maintenance_priority"]}/100'
        )

        print(
            f'   Level    : '
            f'{item["maintenance_level"]}'
        )

        print(
            f'   Severity : '
            f'{item["operational_severity"]}'
        )

        print(
            f'   Action   : '
            f'{item["recommended_action"]}'
        )

        print(
            f'   Reason   : '
            f'{item["reason"]}'
        )

        print(
            "   Human verification :",
            item["human_verification_required"]
        )

        print(
            "   Automatic action    :",
            item["automatic_action"]
        )

    print()
    print("SAFETY / CONTROL BOUNDARY")
    print("-" * 68)
    print("Read-only :", result["read_only"])
    print("SCADA     :", result["scada_control"])

    print()
    print("=" * 68)


if __name__ == "__main__":

    sample = {

        "priority_engine": {

            "ranking": [

                {
                    "equipment": "CV-101",
                    "area": "MBF",

                    "priority_score": 84.7,

                    "severity":
                        "IMMEDIATE ATTENTION",

                    "risk": 82,
                    "criticality": 92,
                    "trend": 76,
                    "evidence": 88,

                    "reason":
                        "Valve position increasing significantly.",

                    "evidence_chain": [
                        "Position changed from 20% to 34%.",
                        "70% increase detected.",
                        "MBF operational correlation."
                    ]
                },

                {
                    "equipment": "FT-301",
                    "area": "PCI",

                    "priority_score": 62.3,

                    "severity":
                        "EARLY WARNING",

                    "risk": 60,
                    "criticality": 65,
                    "trend": 58,
                    "evidence": 62,

                    "reason":
                        "Flow trend requires monitoring.",

                    "evidence_chain": [
                        "Flow trend deviation detected."
                    ]
                }
            ]
        }
    }

    result = build_maintenance_priority(
        sample
    )

    print_maintenance_priority(result)

    print()
    print("=" * 68)
    print("V5.3.0 MODULE TEST: PASS")
    print("=" * 68)
