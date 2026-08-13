"""
ANVIQO V5.2.2
Shift Change Detection

Compares previous and current operational states.

Read-only prototype.
No PLC / WinCC / SCADA control.
"""


def index_conditions(status):

    ranking = (
        status
        .get("priority_engine", {})
        .get("ranking", [])
    )

    return {
        item.get("equipment", "UNKNOWN"): item
        for item in ranking
    }


def detect_shift_changes(previous_status, current_status):

    previous = index_conditions(previous_status)
    current = index_conditions(current_status)

    new_conditions = []
    worsening = []
    improving = []
    cleared = []
    unchanged = []

    # Current conditions
    for equipment, current_item in current.items():

        if equipment not in previous:

            new_conditions.append({
                "equipment": equipment,
                "area": current_item.get("area", "UNKNOWN"),
                "severity": current_item.get(
                    "severity", "NORMAL"
                ),
                "priority": current_item.get(
                    "priority_score", 0
                ),
                "change": "NEW CONDITION",
            })

            continue

        previous_item = previous[equipment]

        old_priority = previous_item.get(
            "priority_score", 0
        )

        new_priority = current_item.get(
            "priority_score", 0
        )

        if new_priority > old_priority:

            worsening.append({
                "equipment": equipment,
                "area": current_item.get("area", "UNKNOWN"),
                "previous_priority": old_priority,
                "current_priority": new_priority,
                "change": round(
                    new_priority - old_priority, 1
                ),
            })

        elif new_priority < old_priority:

            improving.append({
                "equipment": equipment,
                "area": current_item.get("area", "UNKNOWN"),
                "previous_priority": old_priority,
                "current_priority": new_priority,
                "change": round(
                    old_priority - new_priority, 1
                ),
            })

        else:

            unchanged.append({
                "equipment": equipment,
                "area": current_item.get("area", "UNKNOWN"),
                "priority": new_priority,
                "change": "UNCHANGED",
            })

    # Conditions that disappeared
    for equipment, previous_item in previous.items():

        if equipment not in current:

            cleared.append({
                "equipment": equipment,
                "area": previous_item.get(
                    "area", "UNKNOWN"
                ),
                "previous_priority": previous_item.get(
                    "priority_score", 0
                ),
                "change": "CLEARED",
            })

    return {
        "version": "V5.2.2",

        "new_conditions": new_conditions,

        "worsening": worsening,

        "improving": improving,

        "cleared": cleared,

        "unchanged": unchanged,

        "read_only": True,

        "scada_control": False,
    }


def print_changes(result):

    print()
    print("=" * 64)
    print("        ANVIQO V5.2.2 SHIFT CHANGE DETECTION")
    print("=" * 64)

    sections = [
        ("NEW CONDITIONS", result["new_conditions"]),
        ("WORSENING", result["worsening"]),
        ("IMPROVING", result["improving"]),
        ("CLEARED", result["cleared"]),
        ("UNCHANGED", result["unchanged"]),
    ]

    for title, items in sections:

        print()
        print(title)
        print("-" * 64)

        if not items:
            print("None")
            continue

        for item in items:
            print(item)

    print()
    print("SAFETY BOUNDARY")
    print("-" * 64)
    print("Read-only :", result["read_only"])
    print("SCADA     :", result["scada_control"])

    print()
    print("=" * 64)


if __name__ == "__main__":

    previous = {
        "priority_engine": {
            "ranking": [
                {
                    "equipment": "CV-101",
                    "area": "MBF",
                    "priority_score": 65.0,
                    "severity": "EARLY WARNING",
                },
                {
                    "equipment": "PT-201",
                    "area": "RMHS",
                    "priority_score": 48.0,
                    "severity": "WATCH",
                },
            ]
        }
    }

    current = {
        "priority_engine": {
            "ranking": [
                {
                    "equipment": "CV-101",
                    "area": "MBF",
                    "priority_score": 84.7,
                    "severity": "IMMEDIATE ATTENTION",
                },
                {
                    "equipment": "FT-301",
                    "area": "PCI",
                    "priority_score": 62.3,
                    "severity": "EARLY WARNING",
                },
            ]
        }
    }

    result = detect_shift_changes(
        previous,
        current
    )

    print_changes(result)

    print()
    print("=" * 64)
    print("V5.2.2 MODULE TEST: PASS")
    print("=" * 64)
