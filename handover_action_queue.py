"""
ANVIQO V5.2.4
Handover Priority & Action Queue
"""

def build_action_queue(plant_status, changes):

    ranking = (
        plant_status
        .get("priority_engine", {})
        .get("ranking", [])
    )

    queue = {}

    for item in ranking:

        equipment = item.get("equipment", "UNKNOWN")
        severity = item.get("severity", "NORMAL")
        score = item.get("priority_score", 0)

        if severity == "IMMEDIATE ATTENTION":
            level = 1
            action = "IMMEDIATE REVIEW"

        elif severity == "EARLY WARNING":
            level = 2
            action = "MONITOR CLOSELY"

        elif severity == "WATCH":
            level = 3
            action = "CONTINUE MONITORING"

        else:
            level = 4
            action = "NO IMMEDIATE ACTION"

        queue[equipment] = {
            "equipment": equipment,
            "area": item.get("area", "UNKNOWN"),
            "priority": score,
            "severity": severity,
            "action_level": level,
            "action": action,
            "reason": item.get("reason", "")
        }

    for item in changes.get("worsening", []):

        equipment = item.get("equipment", "UNKNOWN")

        if equipment in queue:

            queue[equipment]["action_level"] = 1
            queue[equipment]["action"] = (
                "IMMEDIATE REVIEW — CONDITION WORSENING"
            )
            queue[equipment]["change"] = item.get(
                "change", 0
            )

    for item in changes.get("new_conditions", []):

        equipment = item.get("equipment", "UNKNOWN")

        if equipment in queue:
            queue[equipment]["new_condition"] = True

    for item in changes.get("cleared", []):

        equipment = item.get("equipment", "UNKNOWN")
        queue.pop(equipment, None)

    actions = list(queue.values())

    actions.sort(
        key=lambda x: (
            x["action_level"],
            -x["priority"]
        )
    )

    for number, item in enumerate(actions, 1):
        item["queue_position"] = number

    return {
        "version": "V5.2.4",
        "action_count": len(actions),
        "actions": actions,
        "read_only": True,
        "scada_control": False
    }


def print_action_queue(result):

    print()
    print("=" * 64)
    print("        ANVIQO V5.2.4 ACTION QUEUE")
    print("=" * 64)

    print()
    print("NEXT SHIFT PRIORITIES")
    print("-" * 64)

    if not result["actions"]:
        print("No active actions.")

    for item in result["actions"]:

        print()
        print(
            f'{item["queue_position"]}. '
            f'{item["equipment"]} | '
            f'{item["area"]}'
        )

        print(
            f'   Priority : {item["priority"]}/100'
        )

        print(
            f'   Severity : {item["severity"]}'
        )

        print(
            f'   Action   : {item["action"]}'
        )

        if item.get("new_condition"):
            print("   Change   : NEW CONDITION")

        if "change" in item:
            print(
                f'   Trend    : +{item["change"]}'
            )

        print(
            f'   Reason   : {item["reason"]}'
        )

    print()
    print("ACTION COUNT")
    print("-" * 64)
    print(result["action_count"])

    print()
    print("SAFETY BOUNDARY")
    print("-" * 64)
    print("Read-only :", result["read_only"])
    print("SCADA     :", result["scada_control"])

    print()
    print("=" * 64)


if __name__ == "__main__":

    plant = {
        "priority_engine": {
            "ranking": [
                {
                    "equipment": "CV-101",
                    "area": "MBF",
                    "priority_score": 84.7,
                    "severity": "IMMEDIATE ATTENTION",
                    "reason":
                        "Valve position increasing significantly."
                },
                {
                    "equipment": "FT-301",
                    "area": "PCI",
                    "priority_score": 62.3,
                    "severity": "EARLY WARNING",
                    "reason":
                        "Flow trend requires monitoring."
                },
                {
                    "equipment": "PT-201",
                    "area": "RMHS",
                    "priority_score": 48.0,
                    "severity": "WATCH",
                    "reason":
                        "Pressure trend under observation."
                }
            ]
        }
    }

    changes = {
        "new_conditions": [
            {
                "equipment": "FT-301",
                "area": "PCI"
            }
        ],

        "worsening": [
            {
                "equipment": "CV-101",
                "area": "MBF",
                "change": 19.7
            }
        ],

        "cleared": [
            {
                "equipment": "PT-201",
                "area": "RMHS"
            }
        ]
    }

    result = build_action_queue(
        plant,
        changes
    )

    print_action_queue(result)

    print()
    print("=" * 64)
    print("V5.2.4 MODULE TEST: PASS")
    print("=" * 64)
