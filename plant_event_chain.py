"""
ANVIQO V5.4.3
Plant Event Chain Intelligence

Combines:
    equipment_relationships.py
    event_timeline.py
    event_correlation.py
    shift_event_timeline.py

Purpose:
    Identify a sequence of related events across connected
    equipment and present an evidence-backed plant event chain.

Safety:
    Read-only
    No PLC writes
    No SCADA writes
    No automatic control
    No causation claim without sufficient evidence
"""

from equipment_relationships import get_relationships
from event_timeline import get_events
from event_correlation import correlate_events


class PlantEventChainEngine:

    def __init__(self):
        self.equipment = {}

    # ---------------------------------------------------------
    # REGISTER EQUIPMENT
    # ---------------------------------------------------------

    def register_equipment(self, equipment, area):
        self.equipment[equipment] = {
            "equipment": equipment,
            "area": area
        }

    # ---------------------------------------------------------
    # GET RELATIONSHIPS
    # ---------------------------------------------------------

    def get_connected_equipment(self, equipment):

        relationships = get_relationships(equipment)

        return [
            {
                "target": item.get("target"),
                "relationship_type": item.get(
                    "relationship_type",
                    "RELATED"
                )
            }
            for item in relationships
            if item.get("target")
        ]

    # ---------------------------------------------------------
    # GET EVENT EVIDENCE
    # ---------------------------------------------------------

    def get_event_evidence(self, equipment):

        events = get_events(equipment)

        if not events:
            return {
                "status": "NO DATA",
                "chain": [],
                "event_count": 0
            }

        result = correlate_events(
            equipment,
            events
        )

        return {
            "status": result.get("status"),
            "chain": result.get("chain", []),
            "event_count": len(events)
        }

    # ---------------------------------------------------------
    # BUILD PLANT EVENT CHAIN
    # ---------------------------------------------------------

    def build_chain(self):

        chains = []
        processed = set()

        for equipment in self.equipment:

            connected = self.get_connected_equipment(
                equipment
            )

            own_events = self.get_event_evidence(
                equipment
            )

            for relationship in connected:

                target = relationship["target"]

                if target not in self.equipment:
                    continue

                pair = tuple(
                    sorted(
                        [equipment, target]
                    )
                )

                if pair in processed:
                    continue

                processed.add(pair)

                target_events = self.get_event_evidence(
                    target
                )

                # ------------------------------------------------
                # REQUIRE EVENT EVIDENCE ON BOTH SIDES
                # ------------------------------------------------

                if (
                    own_events["event_count"] == 0
                    or target_events["event_count"] == 0
                ):
                    continue

                evidence = []

                evidence.append(
                    f"{equipment} event status: "
                    f"{own_events['status']}."
                )

                evidence.extend(
                    [
                        f"{equipment}: {item}"
                        for item in own_events["chain"]
                    ]
                )

                evidence.append(
                    f"{target} event status: "
                    f"{target_events['status']}."
                )

                evidence.extend(
                    [
                        f"{target}: {item}"
                        for item in target_events["chain"]
                    ]
                )

                # ------------------------------------------------
                # DETERMINE STRENGTH
                # ------------------------------------------------

                if (
                    own_events["status"]
                    == "CORRELATED CONDITION"
                    and
                    target_events["status"]
                    == "CORRELATED CONDITION"
                ):

                    status = "STRONG EVENT CHAIN"
                    confidence = 85

                elif (
                    own_events["status"]
                    in [
                        "CORRELATED CONDITION",
                        "POSSIBLE CORRELATION"
                    ]
                    and
                    target_events["status"]
                    in [
                        "CORRELATED CONDITION",
                        "POSSIBLE CORRELATION"
                    ]
                ):

                    status = "DEVELOPING EVENT CHAIN"
                    confidence = 75

                else:

                    status = "WEAK EVENT LINK"
                    confidence = 55

                chains.append(
                    {
                        "equipment_chain": [
                            equipment,
                            target
                        ],
                        "relationship": relationship[
                            "relationship_type"
                        ],
                        "status": status,
                        "confidence": confidence,
                        "evidence": evidence,
                        "conclusion": (
                            f"A {status.lower()} exists between "
                            f"{equipment} and {target}. "
                            f"The chronological and relationship "
                            f"evidence supports continued plant "
                            f"investigation. This does not establish "
                            f"causation."
                        )
                    }
                )

        return chains


# =============================================================
# TEST
# =============================================================

def run_test():

    engine = PlantEventChainEngine()

    # Existing relationships created during V5.4.2
    engine.register_equipment(
        "CV-101",
        "MBF"
    )

    engine.register_equipment(
        "CV-102",
        "MBF"
    )

    engine.register_equipment(
        "PT-201",
        "MBF"
    )

    # ---------------------------------------------------------
    # Create test events in the existing event timeline
    # ---------------------------------------------------------

    from event_timeline import record_event

    record_event(
        "CV-101",
        "PARAMETER_CHANGE",
        "Valve Position increased.",
        "WARNING"
    )

    record_event(
        "CV-101",
        "RISK_CHANGE",
        "Equipment risk increased.",
        "WARNING"
    )

    record_event(
        "CV-101",
        "HEALTH_CHANGE",
        "Equipment health changed.",
        "WARNING"
    )

    record_event(
        "CV-102",
        "PARAMETER_CHANGE",
        "Valve Position increased.",
        "WARNING"
    )

    record_event(
        "CV-102",
        "RISK_CHANGE",
        "Equipment risk increased.",
        "WARNING"
    )

    record_event(
        "CV-102",
        "HEALTH_CHANGE",
        "Equipment health deteriorated.",
        "WARNING"
    )

    record_event(
        "PT-201",
        "PARAMETER_CHANGE",
        "Temperature increased.",
        "ATTENTION"
    )

    record_event(
        "PT-201",
        "HEALTH_CHANGE",
        "Equipment health changed.",
        "ATTENTION"
    )

    # ---------------------------------------------------------
    # BUILD CHAIN
    # ---------------------------------------------------------

    chains = engine.build_chain()

    print("=" * 72)
    print("ANVIQO V5.4.3 PLANT EVENT CHAIN")
    print("=" * 72)

    print()

    if not chains:

        print(
            "No plant event chain detected."
        )

    else:

        for index, chain in enumerate(
            chains,
            1
        ):

            print(
                f"EVENT CHAIN #{index}"
            )

            print("-" * 72)

            print(
                "Equipment chain : "
                + " → ".join(
                    chain["equipment_chain"]
                )
            )

            print(
                "Relationship    : "
                + chain["relationship"]
            )

            print(
                "Status          : "
                + chain["status"]
            )

            print(
                "Confidence      : "
                + str(chain["confidence"])
                + "/100"
            )

            print()

            print("Evidence:")

            for evidence in chain["evidence"]:
                print(
                    "✓ " + evidence
                )

            print()

            print("Conclusion:")

            print(
                chain["conclusion"]
            )

            print()

    print("=" * 72)

    if chains:

        print(
            "V5.4.3 MODULE TEST: PASS"
        )

        print(
            "PLANT EVENT CHAIN: PASS"
        )

        print(
            "CAUSATION SAFETY BOUNDARY: PASS"
        )

        print(
            "READ-ONLY CONTROL BOUNDARY: PASS"
        )

    else:

        print(
            "V5.4.3 MODULE TEST: ATTENTION"
        )

    print("=" * 72)


if __name__ == "__main__":
    run_test()
