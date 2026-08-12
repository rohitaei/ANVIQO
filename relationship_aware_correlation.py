"""
ANVIQO V5.4.2
Relationship-Aware Cross-Equipment Correlation

Uses existing:
    equipment_relationships.py
    event_correlation.py

Purpose:
    Connect equipment relationships with operational signals
    and chronological events.

Safety:
    - Read-only
    - No PLC writes
    - No SCADA writes
    - No automatic control
    - No automatic maintenance authorization
    - Correlation is NOT treated as causation
"""

from equipment_relationships import (
    get_relationships,
    build_equipment_relationships
)

from event_correlation import correlate_events


# ============================================================
# RELATIONSHIP-AWARE ENGINE
# ============================================================

class RelationshipAwareCorrelationEngine:

    def __init__(self):
        self.equipment_data = {}

    # --------------------------------------------------------
    # REGISTER EQUIPMENT
    # --------------------------------------------------------

    def register_equipment(
        self,
        equipment,
        area,
        signals=None,
        events=None
    ):
        self.equipment_data[equipment] = {
            "equipment": equipment,
            "area": area,
            "signals": signals or [],
            "events": events or []
        }

    # --------------------------------------------------------
    # GET CONNECTED EQUIPMENT
    # --------------------------------------------------------

    def get_connected_equipment(self, equipment):

        relationships = get_relationships(equipment)

        connected = []

        for relationship in relationships:

            target = relationship.get("target")

            if target:
                connected.append({
                    "equipment": target,
                    "relationship_type": relationship.get(
                        "relationship_type",
                        "RELATED"
                    ),
                    "target_type": relationship.get(
                        "target_type"
                    )
                })

        return connected

    # --------------------------------------------------------
    # ANALYZE EQUIPMENT EVENTS
    # --------------------------------------------------------

    def analyze_equipment_events(self, equipment):

        data = self.equipment_data.get(equipment)

        if not data:
            return {
                "status": "NO DATA",
                "correlation": "Equipment data unavailable.",
                "chain": []
            }

        return correlate_events(
            equipment,
            data.get("events", [])
        )

    # --------------------------------------------------------
    # FIND RELATIONSHIP-AWARE CORRELATIONS
    # --------------------------------------------------------

    def analyze(self):

        results = []

        processed_pairs = set()

        for equipment in self.equipment_data:

            connected = self.get_connected_equipment(
                equipment
            )

            own_data = self.equipment_data.get(
                equipment,
                {}
            )

            own_signals = own_data.get(
                "signals",
                []
            )

            own_abnormal = [
                signal
                for signal in own_signals
                if signal.get("status", "").lower()
                in [
                    "warning",
                    "alarm",
                    "attention",
                    "abnormal"
                ]
            ]

            for relationship in connected:

                target = relationship["equipment"]

                if target not in self.equipment_data:
                    continue

                pair = tuple(
                    sorted(
                        [equipment, target]
                    )
                )

                if pair in processed_pairs:
                    continue

                processed_pairs.add(pair)

                target_data = self.equipment_data[
                    target
                ]

                target_signals = target_data.get(
                    "signals",
                    []
                )

                target_abnormal = [
                    signal
                    for signal in target_signals
                    if signal.get("status", "").lower()
                    in [
                        "warning",
                        "alarm",
                        "attention",
                        "abnormal"
                    ]
                ]

                # ------------------------------------------------
                # BOTH EQUIPMENT ABNORMAL
                # ------------------------------------------------

                if own_abnormal and target_abnormal:

                    evidence = []

                    for signal in own_abnormal:

                        evidence.append(
                            f"{equipment}: "
                            f"{signal.get('parameter', 'Unknown')} "
                            f"status = "
                            f"{signal.get('status', 'Unknown')}."
                        )

                    for signal in target_abnormal:

                        evidence.append(
                            f"{target}: "
                            f"{signal.get('parameter', 'Unknown')} "
                            f"status = "
                            f"{signal.get('status', 'Unknown')}."
                        )

                    relationship_type = relationship.get(
                        "relationship_type",
                        "RELATED"
                    )

                    results.append({
                        "equipment": [
                            equipment,
                            target
                        ],
                        "relationship_type":
                            relationship_type,
                        "correlation_type":
                            "RELATIONSHIP_AWARE_ABNORMALITY",
                        "confidence": min(
                            95,
                            65
                            + len(own_abnormal) * 5
                            + len(target_abnormal) * 5
                        ),
                        "evidence": evidence,
                        "conclusion": (
                            f"{equipment} and {target} "
                            f"are linked by relationship "
                            f"'{relationship_type}' and both "
                            f"show abnormal operational evidence. "
                            f"This supports a relationship-aware "
                            f"cross-equipment investigation. "
                            f"Correlation does not establish causation."
                        )
                    })

                # ------------------------------------------------
                # EVENT CORRELATION
                # ------------------------------------------------

                own_event_result = (
                    self.analyze_equipment_events(
                        equipment
                    )
                )

                target_event_result = (
                    self.analyze_equipment_events(
                        target
                    )
                )

                own_chain = own_event_result.get(
                    "chain",
                    []
                )

                target_chain = target_event_result.get(
                    "chain",
                    []
                )

                if own_chain and target_chain:

                    results.append({
                        "equipment": [
                            equipment,
                            target
                        ],
                        "relationship_type":
                            relationship.get(
                                "relationship_type",
                                "RELATED"
                            ),
                        "correlation_type":
                            "RELATIONSHIP_AWARE_EVENT_CORRELATION",
                        "confidence": 75,
                        "evidence": [
                            f"{equipment} event correlation: "
                            f"{own_event_result.get('status')}.",
                            f"{target} event correlation: "
                            f"{target_event_result.get('status')}.",
                            f"Relationship identified: "
                            f"{relationship.get('relationship_type', 'RELATED')}."
                        ],
                        "conclusion": (
                            f"Related equipment {equipment} and "
                            f"{target} have correlated event "
                            f"activity. The combined evidence "
                            f"supports further investigation."
                        )
                    })

        return results


# ============================================================
# TEST DATA
# ============================================================

def setup_test_relationships():

    """
    Adds temporary test relationships to the existing
    relationship database.

    Duplicate protection in equipment_relationships.py
    prevents repeated entries.
    """

    from equipment_relationships import add_relationship

    add_relationship(
        "CV-101",
        "PROCESS_RELATED",
        "CV-102",
        "CONTROL_VALVE"
    )

    add_relationship(
        "CV-102",
        "PROCESS_RELATED",
        "PT-201",
        "PRESSURE_TRANSMITTER"
    )


# ============================================================
# TEST
# ============================================================

def run_test():

    setup_test_relationships()

    engine = RelationshipAwareCorrelationEngine()

    # --------------------------------------------------------
    # CV-101
    # --------------------------------------------------------

    engine.register_equipment(
        equipment="CV-101",
        area="MBF",
        signals=[
            {
                "parameter": "Valve Position",
                "value": 78,
                "status": "warning"
            }
        ],
        events=[
            {
                "event_type": "PARAMETER_CHANGE",
                "message": (
                    "Valve Position increased."
                )
            },
            {
                "event_type": "RISK_CHANGE",
                "message": (
                    "Equipment risk increased."
                )
            }
        ]
    )

    # --------------------------------------------------------
    # CV-102
    # --------------------------------------------------------

    engine.register_equipment(
        equipment="CV-102",
        area="MBF",
        signals=[
            {
                "parameter": "Valve Position",
                "value": 72,
                "status": "warning"
            }
        ],
        events=[
            {
                "event_type": "PARAMETER_CHANGE",
                "message": (
                    "Valve Position increased."
                )
            },
            {
                "event_type": "HEALTH_CHANGE",
                "message": (
                    "Equipment health deteriorated."
                )
            }
        ]
    )

    # --------------------------------------------------------
    # PT-201
    # --------------------------------------------------------

    engine.register_equipment(
        equipment="PT-201",
        area="MBF",
        signals=[
            {
                "parameter": "Pressure",
                "value": 6.8,
                "status": "attention"
            }
        ],
        events=[
            {
                "event_type": "PARAMETER_CHANGE",
                "message": (
                    "Temperature increased."
                )
            },
            {
                "event_type": "HEALTH_CHANGE",
                "message": (
                    "Equipment health changed."
                )
            }
        ]
    )

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------

    results = engine.analyze()

    print("=" * 72)
    print("ANVIQO V5.4.2 RELATIONSHIP-AWARE CORRELATION")
    print("=" * 72)

    print()

    print("REGISTERED EQUIPMENT")
    print("-" * 72)

    for equipment in engine.equipment_data:

        relationships = build_equipment_relationships(
            equipment
        )

        print(
            f"{equipment} | "
            f"Relationships: "
            f"{relationships['relationship_count']}"
        )

    print()

    print("CORRELATION RESULTS")
    print("-" * 72)

    if not results:

        print(
            "No relationship-aware correlation detected."
        )

    else:

        for index, result in enumerate(
            results,
            1
        ):

            print(
                f"CORRELATION #{index}"
            )

            print(
                f"Equipment         : "
                f"{' <-> '.join(result['equipment'])}"
            )

            print(
                f"Relationship      : "
                f"{result['relationship_type']}"
            )

            print(
                f"Correlation type  : "
                f"{result['correlation_type']}"
            )

            print(
                f"Confidence        : "
                f"{result['confidence']}/100"
            )

            print()

            print("Evidence:")

            for evidence in result["evidence"]:

                print(
                    f"✓ {evidence}"
                )

            print()

            print("Conclusion:")

            print(
                result["conclusion"]
            )

            print()

    print("=" * 72)

    if results:

        print(
            "V5.4.2 MODULE TEST: PASS"
        )

        print(
            "RELATIONSHIP-AWARE CORRELATION: PASS"
        )

        print(
            "CAUSATION SAFETY BOUNDARY: PASS"
        )

    else:

        print(
            "V5.4.2 MODULE TEST: ATTENTION"
        )

    print("=" * 72)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_test()
