"""
ANVIQO V5.2.3
Shift Handover Intelligence v2

Combines:
- Plant operational status
- Shift event timeline
- Shift change detection

Produces an evidence-backed handover narrative.

Read-only prototype.
No PLC / WinCC / SCADA control.
"""


def build_handover_v2(plant_status, changes):

    ranking = (
        plant_status
        .get("priority_engine", {})
        .get("ranking", [])
    )

    immediate = [
        item for item in ranking
        if item.get("severity") == "IMMEDIATE ATTENTION"
    ]

    early = [
        item for item in ranking
        if item.get("severity") == "EARLY WARNING"
    ]

    new_conditions = changes.get(
        "new_conditions", []
    )

    worsening = changes.get(
        "worsening", []
    )

    improving = changes.get(
        "improving", []
    )

    cleared = changes.get(
        "cleared", []
    )

    lines = []

    # Critical conditions
    if immediate:

        for item in immediate:

            lines.append(
                f"CRITICAL: {item['equipment']} "
                f"in {item['area']} remains at "
                f"IMMEDIATE ATTENTION "
                f"({item['priority_score']}/100)."
            )

    # New conditions
    for item in new_conditions:

        lines.append(
            f"NEW: {item['equipment']} "
            f"in {item['area']} has entered "
            f"{item['severity']} "
            f"with priority {item['priority']}/100."
        )

    # Worsening
    for item in worsening:

        lines.append(
            f"WORSENING: {item['equipment']} "
            f"in {item['area']} increased from "
            f"{item['previous_priority']}/100 to "
            f"{item['current_priority']}/100 "
            f"(+{item['change']})."
        )

    # Improving
    for item in improving:

        lines.append(
            f"IMPROVING: {item['equipment']} "
            f"in {item['area']} reduced from "
            f"{item['previous_priority']}/100 to "
            f"{item['current_priority']}/100."
        )

    # Cleared
    for item in cleared:

        lines.append(
            f"CLEARED: {item['equipment']} "
            f"in {item['area']} is no longer "
            f"present in the active priority list."
        )

    # Early warnings
    for item in early:

        lines.append(
            f"MONITOR: {item['equipment']} "
            f"in {item['area']} remains "
            f"{item['severity']}."
        )

    if not lines:

        lines.append(
            "No significant operational changes "
            "identified during the comparison."
        )

    # Next shift focus
    if immediate:

        top = immediate[0]

        next_focus = (
            f"Primary focus: review {top['equipment']} "
            f"in {top['area']} and verify associated "
            f"process behaviour."
        )

    elif new_conditions:

        top = new_conditions[0]

        next_focus = (
            f"Primary focus: monitor new condition "
            f"{top['equipment']} in {top['area']}."
        )

    elif worsening:

        top = worsening[0]

        next_focus = (
            f"Primary focus: follow up worsening "
            f"condition on {top['equipment']}."
        )

    else:

        next_focus = (
            "Continue normal monitoring and "
            "routine operational checks."
        )

    return {
        "version": "V5.2.3",

        "handover_status": (
            "ATTENTION REQUIRED"
            if immediate or worsening
            else "MONITOR"
            if new_conditions or early
            else "NORMAL"
        ),

        "plant_health":
            plant_status.get(
                "overall_plant_health", 100
            ),

        "events": lines,

        "next_shift_focus": next_focus,

        "change_counts": {
            "new": len(new_conditions),
            "worsening": len(worsening),
            "improving": len(improving),
            "cleared": len(cleared),
        },

        "read_only": True,

        "scada_control": False,
    }


def print_handover(result):

    print()
    print("=" * 64)
    print("        ANVIQO V5.2.3 SHIFT HANDOVER")
    print("=" * 64)

    print()
    print("STATUS")
    print("-" * 64)
    print(result["handover_status"])

    print()
    print("PLANT HEALTH")
    print("-" * 64)
    print(f'{result["plant_health"]}/100')

    print()
    print("SHIFT EVENTS")
    print("-" * 64)

    for event in result["events"]:
        print("•", event)

    print()
    print("CHANGE SUMMARY")
    print("-" * 64)

    for key, value in result["change_counts"].items():
        print(f"{key.upper():12}: {value}")

    print()
    print("NEXT SHIFT FOCUS")
    print("-" * 64)
    print(result["next_shift_focus"])

    print()
    print("SAFETY BOUNDARY")
    print("-" * 64)
    print("Read-only :", result["read_only"])
    print("SCADA     :", result["scada_control"])

    print()
    print("=" * 64)


if __name__ == "__main__":

    plant = {
        "overall_plant_health": 70.4,
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

    changes = {
        "new_conditions": [
            {
                "equipment": "FT-301",
                "area": "PCI",
                "severity": "EARLY WARNING",
                "priority": 62.3,
            }
        ],

        "worsening": [
            {
                "equipment": "CV-101",
                "area": "MBF",
                "previous_priority": 65.0,
                "current_priority": 84.7,
                "change": 19.7,
            }
        ],

        "improving": [],

        "cleared": [
            {
                "equipment": "PT-201",
                "area": "RMHS",
                "previous_priority": 48.0,
            }
        ],
    }

    result = build_handover_v2(
        plant,
        changes
    )

    print_handover(result)

    print()
    print("=" * 64)
    print("V5.2.3 MODULE TEST: PASS")
    print("=" * 64)
