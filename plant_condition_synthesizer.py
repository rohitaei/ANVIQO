"""
ANVIQO V5.4.4
Plant Condition Synthesizer

Combines:
    V5.4.1 Cross-Equipment Correlation
    V5.4.2 Relationship-Aware Correlation
    V5.4.3 Plant Event Chain
    Existing Plant Brain reasoning

Purpose:
    Produce one explainable plant-level condition from
    multiple evidence sources.

Safety:
    Read-only
    No PLC writes
    No SCADA writes
    No automatic control
    Human decision remains mandatory
"""

from datetime import datetime

from plant_brain_reasoning import build_plant_brain

from relationship_aware_correlation import (
    RelationshipAwareCorrelationEngine
)

from plant_event_chain import (
    PlantEventChainEngine
)


# ============================================================
# PLANT CONDITION SYNTHESIZER
# ============================================================

class PlantConditionSynthesizer:

    def __init__(self, area):

        self.area = area

    # --------------------------------------------------------
    # BUILD PLANT BRAIN EVIDENCE
    # --------------------------------------------------------

    def get_plant_brain(self):

        return build_plant_brain(
            self.area
        )

    # --------------------------------------------------------
    # BUILD RELATIONSHIP CORRELATION
    # --------------------------------------------------------

    def get_relationship_correlation(
        self,
        equipment_data
    ):

        engine = RelationshipAwareCorrelationEngine()

        for item in equipment_data:

            engine.register_equipment(
                equipment=item["equipment"],
                area=self.area,
                signals=item.get(
                    "signals",
                    []
                ),
                events=item.get(
                    "events",
                    []
                )
            )

        return engine.analyze()

    # --------------------------------------------------------
    # BUILD EVENT CHAIN
    # --------------------------------------------------------

    def get_event_chain(
        self,
        equipment_data
    ):

        engine = PlantEventChainEngine()

        for item in equipment_data:

            engine.register_equipment(
                equipment=item["equipment"],
                area=self.area
            )

        return engine.build_chain()

    # --------------------------------------------------------
    # SYNTHESIZE CONDITION
    # --------------------------------------------------------

    def synthesize(
        self,
        equipment_data
    ):

        plant_brain = self.get_plant_brain()

        relationships = self.get_relationship_correlation(
            equipment_data
        )

        event_chains = self.get_event_chain(
            equipment_data
        )

        evidence = []

        # ----------------------------------------------------
        # PLANT BRAIN
        # ----------------------------------------------------

        if plant_brain.get("status") == (
            "PLANT BRAIN EVIDENCE"
        ):

            evidence.append(
                "Plant Brain identified equipment-level "
                "risk and health evidence."
            )

            primary = plant_brain.get(
                "primary_equipment"
            )

            if primary:

                evidence.append(
                    f"Primary equipment contributor: "
                    f"{primary.get('tag')}."
                )

        # ----------------------------------------------------
        # RELATIONSHIP EVIDENCE
        # ----------------------------------------------------

        for result in relationships:

            evidence.append(
                "Relationship-aware correlation detected "
                f"between "
                f"{' and '.join(result['equipment'])}."
            )

            evidence.append(
                f"Relationship type: "
                f"{result['relationship_type']}."
            )

        # ----------------------------------------------------
        # EVENT CHAIN EVIDENCE
        # ----------------------------------------------------

        for chain in event_chains:

            evidence.append(
                "Plant event chain detected across "
                f"{' and '.join(chain['equipment_chain'])}."
            )

            evidence.append(
                f"Event chain status: "
                f"{chain['status']}."
            )

        # ----------------------------------------------------
        # INVOLVED EQUIPMENT
        # ----------------------------------------------------

        involved = []

        for item in equipment_data:

            tag = item.get(
                "equipment"
            )

            if tag and tag not in involved:

                involved.append(tag)

        for result in relationships:

            for tag in result.get(
                "equipment",
                []
            ):

                if tag not in involved:

                    involved.append(tag)

        for chain in event_chains:

            for tag in chain.get(
                "equipment_chain",
                []
            ):

                if tag not in involved:

                    involved.append(tag)

        # ----------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------

        evidence_sources = 0

        if plant_brain.get("status") == (
            "PLANT BRAIN EVIDENCE"
        ):
            evidence_sources += 1

        if relationships:
            evidence_sources += 1

        if event_chains:
            evidence_sources += 1

        if evidence_sources >= 3:

            confidence = 88
            confidence_level = "HIGH"

        elif evidence_sources == 2:

            confidence = 75
            confidence_level = "MEDIUM"

        elif evidence_sources == 1:

            confidence = 60
            confidence_level = "LOW"

        else:

            confidence = 0
            confidence_level = "INSUFFICIENT"

        # ----------------------------------------------------
        # CONDITION
        # ----------------------------------------------------

        if confidence >= 75:

            condition = (
                "DEVELOPING CROSS-EQUIPMENT "
                "PLANT CONDITION"
            )

            decision = (
                "MANAGEMENT REVIEW RECOMMENDED"
            )

        elif confidence >= 60:

            condition = (
                "EARLY PLANT CONDITION"
            )

            decision = (
                "CONTINUE MONITORING AND REVIEW"
            )

        else:

            condition = (
                "INSUFFICIENT PLANT EVIDENCE"
            )

            decision = (
                "NO MANAGEMENT DECISION"
            )

        # ----------------------------------------------------
        # SAFETY
        # ----------------------------------------------------

        return {
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),

            "area": self.area,

            "condition": condition,

            "involved_equipment": involved,

            "evidence": evidence,

            "evidence_sources": evidence_sources,

            "confidence": confidence,

            "confidence_level": confidence_level,

            "decision": decision,

            "human_decision_required": True,

            "read_only": True,

            "plc_write": False,

            "scada_write": False,

            "causation_established": False,

            "plant_brain": plant_brain,

            "relationship_correlations": relationships,

            "event_chains": event_chains
        }


# ============================================================
# TEST
# ============================================================

def run_test():

    synthesizer = PlantConditionSynthesizer(
        "MBF"
    )

    equipment_data = [

        {
            "equipment": "CV-101",
            "signals": [
                {
                    "parameter": "Valve Position",
                    "value": 78,
                    "status": "warning"
                }
            ],
            "events": [
                {
                    "event_type": "PARAMETER_CHANGE",
                    "message":
                        "Valve Position increased."
                },
                {
                    "event_type": "RISK_CHANGE",
                    "message":
                        "Equipment risk increased."
                },
                {
                    "event_type": "HEALTH_CHANGE",
                    "message":
                        "Equipment health deteriorated."
                }
            ]
        },

        {
            "equipment": "CV-102",
            "signals": [
                {
                    "parameter": "Valve Position",
                    "value": 72,
                    "status": "warning"
                }
            ],
            "events": [
                {
                    "event_type": "PARAMETER_CHANGE",
                    "message":
                        "Valve Position increased."
                },
                {
                    "event_type": "RISK_CHANGE",
                    "message":
                        "Equipment risk increased."
                },
                {
                    "event_type": "HEALTH_CHANGE",
                    "message":
                        "Equipment health deteriorated."
                }
            ]
        },

        {
            "equipment": "PT-201",
            "signals": [
                {
                    "parameter": "Pressure",
                    "value": 6.8,
                    "status": "attention"
                }
            ],
            "events": [
                {
                    "event_type": "PARAMETER_CHANGE",
                    "message":
                        "Temperature increased."
                },
                {
                    "event_type": "HEALTH_CHANGE",
                    "message":
                        "Equipment health changed."
                }
            ]
        }
    ]

    result = synthesizer.synthesize(
        equipment_data
    )

    print("=" * 72)
    print("ANVIQO V5.4.4 PLANT CONDITION SYNTHESIZER")
    print("=" * 72)

    print()

    print(
        f"Area                : "
        f"{result['area']}"
    )

    print(
        f"Condition           : "
        f"{result['condition']}"
    )

    print(
        f"Confidence          : "
        f"{result['confidence']}/100 "
        f"({result['confidence_level']})"
    )

    print(
        f"Decision            : "
        f"{result['decision']}"
    )

    print()

    print("INVOLVED EQUIPMENT")
    print("-" * 72)

    for equipment in result[
        "involved_equipment"
    ]:

        print(
            f"✓ {equipment}"
        )

    print()

    print("EVIDENCE")
    print("-" * 72)

    for item in result["evidence"]:

        print(
            f"✓ {item}"
        )

    print()

    print("SAFETY / CONTROL BOUNDARY")
    print("-" * 72)

    print(
        "Human decision required : "
        f"{result['human_decision_required']}"
    )

    print(
        "Read-only              : "
        f"{result['read_only']}"
    )

    print(
        "PLC write              : "
        f"{result['plc_write']}"
    )

    print(
        "SCADA write            : "
        f"{result['scada_write']}"
    )

    print(
        "Causation established  : "
        f"{result['causation_established']}"
    )

    print()

    print("=" * 72)

    if (
        result["confidence"] >= 75
        and result["human_decision_required"]
        and result["read_only"]
        and not result["plc_write"]
        and not result["scada_write"]
        and not result["causation_established"]
    ):

        print(
            "V5.4.4 MODULE TEST: PASS"
        )

        print(
            "PLANT CONDITION SYNTHESIS: PASS"
        )

        print(
            "EVIDENCE INTEGRATION: PASS"
        )

        print(
            "SAFETY BOUNDARY: PASS"
        )

    else:

        print(
            "V5.4.4 MODULE TEST: ATTENTION"
        )

    print("=" * 72)


if __name__ == "__main__":
    run_test()
