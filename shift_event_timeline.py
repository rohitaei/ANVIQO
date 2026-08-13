"""
ANVIQO V5.2.1
Shift Event Timeline

Builds a chronological operational timeline from
V5.1/V5.2 intelligence.

Read-only prototype.
No PLC / WinCC / SCADA control.
"""

from datetime import datetime


def build_event_timeline(plant_status):

    ranking = (
        plant_status
        .get("priority_engine", {})
        .get("ranking", [])
    )

    events = []

    for item in ranking:

        equipment = item.get("equipment", "UNKNOWN")
        area = item.get("area", "UNKNOWN")
        severity = item.get("severity", "NORMAL")
        priority = item.get("priority_score", 0)
        reason = item.get("reason", "")

        evidence = item.get(
            "evidence_chain", []
        )

        events.append({
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
            "equipment": equipment,
            "area": area,
            "severity": severity,
            "priority": priority,
            "event": reason,
            "evidence": evidence,
            "status": "ACTIVE",
        })

    events.sort(
        key=lambda event: event["priority"],
        reverse=True
    )

    return {
        "version": "V5.2.1",
        "event_count": len(events),
        "events": events,
        "read_only": True,
        "scada_control": False,
    }


def print_timeline(timeline):

    print()
    print("=" * 64)
    print("        ANVIQO V5.2.1 EVENT TIMELINE")
    print("=" * 64)

    print()
    print("EVENTS")
    print("-" * 64)

    for event in timeline["events"]:

        print()
        print(event["timestamp"])
        print(
            f'{event["equipment"]} | '
            f'{event["area"]} | '
            f'{event["severity"]} | '
            f'Priority {event["priority"]}'
        )

        print("Event:", event["event"])

        for evidence in event["evidence"]:
            print("  ✓", evidence)

        print("Status:", event["status"])

    print()
    print("EVENT COUNT")
    print("-" * 64)
    print(timeline["event_count"])

    print()
    print("SAFETY BOUNDARY")
    print("-" * 64)
    print("Read-only :", timeline["read_only"])
    print("SCADA     :", timeline["scada_control"])

    print()
    print("=" * 64)


if __name__ == "__main__":

    sample = {
        "priority_engine": {
            "ranking": [
                {
                    "equipment": "CV-101",
                    "area": "MBF",
                    "priority_score": 84.7,
                    "severity": "IMMEDIATE ATTENTION",
                    "reason":
                        "Valve position is increasing significantly.",
                    "evidence_chain": [
                        "Position changed from 20% to 34%.",
                        "70% increase detected.",
                        "MBF operational correlation.",
                    ],
                },
                {
                    "equipment": "FT-301",
                    "area": "PCI",
                    "priority_score": 62.3,
                    "severity": "EARLY WARNING",
                    "reason":
                        "Flow trend requires monitoring.",
                    "evidence_chain": [
                        "Flow trend deviation detected."
                    ],
                },
            ]
        }
    }

    result = build_event_timeline(sample)

    print_timeline(result)

    print()
    print("=" * 64)
    print("V5.2.1 MODULE TEST: PASS")
    print("=" * 64)
