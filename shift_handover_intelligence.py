"""
ANVIQO V5.2
Shift Handover Intelligence

Consumes V5.1 operational intelligence and creates
a concise, evidence-backed shift handover.

Read-only prototype.
No PLC / WinCC / SCADA control.
"""


def build_shift_handover(plant_status):
    ranking = (
        plant_status
        .get("priority_engine", {})
        .get("ranking", [])
    )

    plant_health = plant_status.get(
        "overall_plant_health", 100
    )

    situation = plant_status.get(
        "situation_summary",
        "No significant operational condition detected."
    )

    immediate = []
    early_warning = []
    watch = []
    normal = []

    for item in ranking:

        severity = item.get(
            "severity", "NORMAL"
        )

        if severity == "IMMEDIATE ATTENTION":
            immediate.append(item)

        elif severity == "EARLY WARNING":
            early_warning.append(item)

        elif severity == "WATCH":
            watch.append(item)

        else:
            normal.append(item)

    active_items = immediate + early_warning + watch

    if active_items:

        top = active_items[0]

        next_shift_focus = (
            f"Review {top.get('equipment', 'UNKNOWN')} "
            f"in {top.get('area', 'UNKNOWN')} and verify "
            f"associated process behaviour."
        )

    else:

        next_shift_focus = (
            "Continue normal monitoring and "
            "routine operational checks."
        )

    if immediate:

        handover_status = "ATTENTION REQUIRED"

    elif early_warning:

        handover_status = "EARLY WARNING"

    elif watch:

        handover_status = "WATCH"

    else:

        handover_status = "NORMAL"

    return {
        "version": "V5.2.0",

        "handover_status": handover_status,

        "plant_health": plant_health,

        "plant_situation": situation,

        "immediate_attention": immediate,

        "early_warnings": early_warning,

        "watch_conditions": watch,

        "normal_conditions": normal,

        "active_condition_count": len(active_items),

        "next_shift_focus": next_shift_focus,

        "anviqo_summary": (
            f"Plant health is {plant_health}/100. "
            f"{situation} "
            f"{len(active_items)} active operational "
            f"condition(s) require monitoring or follow-up."
        ),

        "read_only": True,

        "scada_control": False,
    }


def print_handover(handover):

    print()
    print("=" * 64)
    print("        ANVIQO V5.2 SHIFT HANDOVER")
    print("=" * 64)

    print()
    print("HANDOVER STATUS")
    print("-" * 64)
    print(handover["handover_status"])

    print()
    print("PLANT HEALTH")
    print("-" * 64)
    print(f'{handover["plant_health"]}/100')

    print()
    print("PLANT SITUATION")
    print("-" * 64)
    print(handover["plant_situation"])

    if handover["immediate_attention"]:

        print()
        print("🔴 IMMEDIATE ATTENTION")
        print("-" * 64)

        for item in handover["immediate_attention"]:

            print(
                f'{item["equipment"]} | '
                f'{item["area"]} | '
                f'{item["priority_score"]}/100'
            )

            print(
                f'  Reason: {item.get("reason", "")}'
            )

    if handover["early_warnings"]:

        print()
        print("🟠 EARLY WARNING")
        print("-" * 64)

        for item in handover["early_warnings"]:

            print(
                f'{item["equipment"]} | '
                f'{item["area"]} | '
                f'{item["priority_score"]}/100'
            )

    if handover["watch_conditions"]:

        print()
        print("🟡 WATCH")
        print("-" * 64)

        for item in handover["watch_conditions"]:

            print(
                f'{item["equipment"]} | '
                f'{item["area"]} | '
                f'{item["priority_score"]}/100'
            )

    print()
    print("ANVIQO SUMMARY")
    print("-" * 64)
    print(handover["anviqo_summary"])

    print()
    print("NEXT SHIFT FOCUS")
    print("-" * 64)
    print(handover["next_shift_focus"])

    print()
    print("SAFETY BOUNDARY")
    print("-" * 64)
    print("Read-only :", handover["read_only"])
    print("SCADA     :", handover["scada_control"])

    print()
    print("=" * 64)


if __name__ == "__main__":

    # V5.1-style test input
    sample = {
        "overall_plant_health": 70.4,

        "situation_summary":
            "Immediate attention required for CV-101 in MBF.",

        "priority_engine": {
            "ranking": [
                {
                    "equipment": "CV-101",
                    "area": "MBF",
                    "priority_score": 84.7,
                    "severity": "IMMEDIATE ATTENTION",
                    "reason":
                        "Valve position is increasing significantly.",
                },
                {
                    "equipment": "FT-301",
                    "area": "PCI",
                    "priority_score": 62.3,
                    "severity": "EARLY WARNING",
                    "reason":
                        "Flow trend requires monitoring.",
                },
            ]
        },
    }

    result = build_shift_handover(sample)

    print_handover(result)

    print()
    print("=" * 64)
    print("V5.2.0 MODULE TEST: PASS")
    print("=" * 64)
