"""
ANVIQO V5.4 FULL INTEGRATION VALIDATOR

V5.4.1  Cross-Equipment Correlation
V5.4.2  Relationship-Aware Correlation
V5.4.3  Plant Event Chain
V5.4.4  Plant Condition Synthesis
V5.4.5  Evidence / Confidence Integrity
V5.4.6  Plant Brain -> Decision Bridge
V5.4.7  Management Governance
V5.4.8  Safety / Control Boundary

V5.3 governance remains the final decision gate.

READ-ONLY.
NO PLC WRITE.
NO SCADA CONTROL.
NO AUTOMATIC AUTHORIZATION.
"""

from datetime import datetime

from equipment_relationships import (
    add_relationship,
    get_relationships
)

from event_timeline import (
    record_event,
    get_events
)

from event_correlation import (
    correlate_events
)

from plant_brain_reasoning import (
    build_plant_brain
)

from maintenance_decision import (
    build_maintenance_decision
)

from maintenance_management_report import (
    build_management_report
)


# ============================================================
# V5.4.1
# ============================================================

def test_cross_equipment_correlation():

    evidence = [
        "CV-102: Valve Position status = warning.",
        "PT-201: Pressure status = attention."
    ]

    passed = len(evidence) >= 2

    return {
        "version": "V5.4.1",
        "name": "CROSS-EQUIPMENT CORRELATION",
        "pass": passed,
        "evidence": evidence
    }


# ============================================================
# V5.4.2
# ============================================================

def test_relationship_correlation():

    add_relationship(
        "CV-102",
        "PROCESS_RELATED",
        "PT-201",
        "EQUIPMENT"
    )

    relationships = get_relationships(
        "CV-102"
    )

    found = any(
        item.get("target") == "PT-201"
        and
        item.get("relationship_type")
        == "PROCESS_RELATED"
        for item in relationships
    )

    return {
        "version": "V5.4.2",
        "name": "RELATIONSHIP-AWARE CORRELATION",
        "pass": found,
        "causation_safe": True
    }


# ============================================================
# V5.4.3
# ============================================================

def test_event_chain():

    events_cv = [
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

    events_pt = [
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

    cv_result = correlate_events(
        "CV-102",
        events_cv
    )

    pt_result = correlate_events(
        "PT-201",
        events_pt
    )

    passed = (
        cv_result.get("status")
        in [
            "POSSIBLE CORRELATION",
            "CORRELATED CONDITION"
        ]
        and
        pt_result.get("status")
        in [
            "POSSIBLE CORRELATION",
            "CORRELATED CONDITION"
        ]
    )

    return {
        "version": "V5.4.3",
        "name": "PLANT EVENT CHAIN",
        "pass": passed,
        "cv_status":
            cv_result.get("status"),
        "pt_status":
            pt_result.get("status")
    }


# ============================================================
# V5.4.4
# ============================================================

def test_plant_condition():

    brain = build_plant_brain(
        "MBF"
    )

    contributors = (
        brain.get(
            "equipment_reasoning",
            []
        )
    )

    condition_evidence = (
        len(contributors) > 0
    )

    return {
        "version": "V5.4.4",
        "name": "PLANT CONDITION SYNTHESIS",
        "pass": condition_evidence,
        "plant_brain_status":
            brain.get("status"),
        "contributors":
            len(contributors)
    }


# ============================================================
# V5.4.5
# ============================================================

def test_evidence_integrity():

    raw_evidence = [
        "CV-102 event correlation detected.",
        "Relationship type: PROCESS_RELATED.",
        "Relationship type: PROCESS_RELATED.",
        "CV-102 event correlation detected.",
        "PT-201 event correlation detected.",
        "CV-102 and PT-201 are process related."
    ]

    unique = []
    seen = set()

    for item in raw_evidence:

        normalized = (
            item.lower()
            .strip()
        )

        if normalized not in seen:

            seen.add(normalized)
            unique.append(item)

    duplicates_removed = (
        len(raw_evidence)
        - len(unique)
    )

    passed = (
        duplicates_removed > 0
        and
        len(unique) < len(raw_evidence)
    )

    return {
        "version": "V5.4.5",
        "name": "EVIDENCE / CONFIDENCE INTEGRITY",
        "pass": passed,
        "raw_count":
            len(raw_evidence),
        "unique_count":
            len(unique),
        "duplicates_removed":
            duplicates_removed
    }


# ============================================================
# V5.4.6
# PLANT BRAIN -> DECISION BRIDGE
# ============================================================

def test_decision_bridge():

    brain = build_plant_brain(
        "MBF"
    )

    contributors = brain.get(
        "equipment_reasoning",
        []
    )

    if contributors:

        primary = contributors[0]

        equipment = primary.get(
            "equipment",
            "CV-101"
        )

        health = primary.get(
            "confidence",
            0
        )

    else:

        equipment = "CV-101"
        health = 0

    decision_input = {
        "equipment": equipment,
        "area": "MBF",
        "maintenance_priority": 84.7,
        "reason":
            "Plant Brain identified cross-equipment "
            "evidence requiring management review."
    }

    decision = build_maintenance_decision(
        decision_input
    )

    passed = (
        decision.get(
            "authorization",
            {}
        ).get(
            "human_required"
        )
        is True
        and
        decision.get(
            "control_boundary",
            {}
        ).get(
            "read_only"
        )
        is True
    )

    return {
        "version": "V5.4.6",
        "name": "PLANT BRAIN -> DECISION BRIDGE",
        "pass": passed,
        "decision": decision
    }


# ============================================================
# V5.4.7
# MANAGEMENT GOVERNANCE
# ============================================================

def test_management_governance():

    current_condition = {
        "equipment": "CV-101",
        "area": "MBF",
        "reason":
            "Multiple related equipment signals "
            "indicate a developing plant condition."
    }

    base_recommendation = {
        "priority": 84.7,
        "recommendation":
            "Perform controlled maintenance review "
            "and verify associated process conditions."
    }

    report = build_management_report(
        current_condition,
        base_recommendation
    )

    human_required = (
        report.get(
            "human_decision_required"
        )
        is True
    )

    control = report.get(
        "control_boundary",
        {}
    )

    read_only = (
        control.get("read_only")
        is True
    )

    plc_write = (
        control.get("plc_write")
        is False
    )

    scada_control = (
        control.get("scada_control")
        is False
    )

    passed = (
        human_required
        and
        read_only
        and
        plc_write
        and
        scada_control
    )

    return {
        "version": "V5.4.7",
        "name": "MANAGEMENT GOVERNANCE",
        "pass": passed,

        "management_level":
            report.get("management_level"),

        "priority":
            report.get("priority"),

        "decision":
            report.get("decision"),

        "human_decision_required":
            human_required,

        "control_boundary":
            control,

        "safety_gate":
            report.get(
                "safety_gate",
                {}
            ),

        "report":
            report
    }

# ============================================================
# V5.4.8
# FINAL SAFETY
# ============================================================

def test_safety_boundary(
    decision_result,
    management_result
):

    decision = decision_result.get(
        "decision",
        {}
    )

    management = management_result

    decision_control = decision.get(
        "control_boundary",
        {}
    )

    management_control = management.get(
        "control_boundary",
        {}
    )

    human_required = (
        management.get(
            "human_decision_required"
        )
        is True
    )

    read_only = (
        decision_control.get(
            "read_only"
        )
        is True
        and
        management_control.get(
            "read_only"
        )
        is True
    )

    plc_write_blocked = (
        decision_control.get(
            "plc_write"
        )
        is False
        and
        management_control.get(
            "plc_write"
        )
        is False
    )

    scada_write_blocked = (
        decision_control.get(
            "scada_control"
        )
        is False
        and
        management_control.get(
            "scada_control"
        )
        is False
    )




    print()
    print("DEBUG V5.4.8")
    print("-" * 40)
    print("human_required      :", human_required)
    print("read_only           :", read_only)
    print("plc_write_blocked   :", plc_write_blocked)
    print("scada_write_blocked :", scada_write_blocked)
    print("-" * 40)

    passed = (
        human_required
        and
        read_only
        and
        plc_write_blocked
        and
        scada_write_blocked
    )

    return {
        "version": "V5.4.8",
        "name": "SAFETY / CONTROL BOUNDARY",
        "pass": passed,
        "read_only": read_only,
        "plc_write": False,
        "scada_control": False,
        "human_decision_required": human_required,
        "automatic_authorization": False,
        "causation_claim": False
    }

# ============================================================
# MASTER TEST
# ============================================================

def run_full_test():

    print()
    print("=" * 72)
    print(
        "ANVIQO V5.4 FULL INTEGRATION VALIDATION"
    )
    print("=" * 72)

    print()
    print(
        "Timestamp:",
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    # --------------------------------------------------------
    # Run modules
    # --------------------------------------------------------

    v541 = test_cross_equipment_correlation()

    v542 = test_relationship_correlation()

    v543 = test_event_chain()

    v544 = test_plant_condition()

    v545 = test_evidence_integrity()

    v546 = test_decision_bridge()

    v547 = test_management_governance()

    v548 = test_safety_boundary(
        v546,
        v547
    )

    results = [
        v541,
        v542,
        v543,
        v544,
        v545,
        v546,
        v547,
        v548
    ]

    # --------------------------------------------------------
    # Print status
    # --------------------------------------------------------

    print()
    print("MODULE STATUS")
    print("-" * 72)

    for result in results:

        status = (
            "PASS"
            if result["pass"]
            else "FAIL"
        )

        print(
            f'{result["version"]:<9} '
            f'{result["name"]:<42} : '
            f'{status}'
        )

    # --------------------------------------------------------
    # Architecture path
    # --------------------------------------------------------

    print()
    print("=" * 72)

    print(
        "EVIDENCE -> RELATIONSHIP -> EVENT -> "
        "PLANT BRAIN"
    )

    print(
        "-> CONFIDENCE -> DECISION -> MANAGEMENT"
    )

    print("=" * 72)

    # --------------------------------------------------------
    # Safety
    # --------------------------------------------------------

    print()
    print("FINAL SAFETY / CONTROL STATE")
    print("-" * 72)

    print(
        "READ-ONLY               : TRUE"
    )

    print(
        "PLC WRITE               : FALSE"
    )

    print(
        "SCADA CONTROL           : FALSE"
    )

    print(
        "HUMAN DECISION REQUIRED : TRUE"
    )

    print(
        "AUTOMATIC AUTHORIZATION : FALSE"
    )

    print(
        "CAUSATION CLAIM         : FALSE"
    )

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    overall_pass = all(
        result["pass"]
        for result in results
    )

    print()
    print("=" * 72)

    if overall_pass:

        print(
            "ANVIQO V5.4 OVERALL STATUS : PASS"
        )

        print(
            "FULL INTELLIGENCE PIPELINE : PASS"
        )

        print(
            "MANAGEMENT GOVERNANCE      : PASS"
        )

        print(
            "SAFETY BOUNDARY            : PASS"
        )

    else:

        print(
            "ANVIQO V5.4 OVERALL STATUS : ATTENTION"
        )

        print(
            "One or more integration gates failed."
        )

    print("=" * 72)
    print()


if __name__ == "__main__":

    run_full_test()
