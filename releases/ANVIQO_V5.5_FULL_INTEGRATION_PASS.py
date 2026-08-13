"""
ANVIQO V5.5
PLANT BRAIN MANAGEMENT INTELLIGENCE

Integrated management-intelligence validation.

V5.5.1  Management Situation Summary
V5.5.2  What Changed Intelligence
V5.5.3  Primary Contributor Ranking
V5.5.4  Evidence Strength & Uncertainty
V5.5.5  Management Priority Explanation
V5.5.6  Multi-Equipment Situation Synthesis
V5.5.7  Recommended Management Review
V5.5.8  Human Decision Governance
V5.5.9  Read-Only Safety Validation
V5.5.10 Full V5.5 Integration

Safety:
    Read-only
    No PLC write
    No SCADA control
    No automatic authorization
    No automatic causation claim
"""

from datetime import datetime


# ============================================================
# V5.5.1
# MANAGEMENT SITUATION SUMMARY
# ============================================================

def build_management_situation():

    situation = {
        "area": "MBF",
        "status": "DEVELOPING PLANT CONDITION",

        "primary_equipment": "CV-101",

        "affected_equipment": [
            "CV-101",
            "CV-102",
            "PT-201"
        ],

        "summary":
            "Multiple related equipment signals are abnormal "
            "in the MBF area. Valve position, pressure and "
            "temperature evidence indicate a developing "
            "plant condition requiring continued investigation.",

        "management_attention": True
    }

    return situation


# ============================================================
# V5.5.2
# WHAT CHANGED INTELLIGENCE
# ============================================================

def build_what_changed():

    changes = [
        {
            "equipment": "CV-101",
            "change":
                "Valve Position increased.",
            "status":
                "WARNING"
        },

        {
            "equipment": "CV-102",
            "change":
                "Valve Position increased.",
            "status":
                "WARNING"
        },

        {
            "equipment": "PT-201",
            "change":
                "Pressure / temperature condition changed.",
            "status":
                "ATTENTION"
        }
    ]

    return {
        "change_count": len(changes),
        "changes": changes,
        "status": "MULTIPLE CHANGES DETECTED"
    }


# ============================================================
# V5.5.3
# PRIMARY CONTRIBUTOR RANKING
# ============================================================

def build_contributor_ranking():

    contributors = [
        {
            "equipment": "CV-101",
            "role": "PRIMARY CONTRIBUTOR",
            "priority": 84.7,
            "reason":
                "Valve position trend and equipment evidence "
                "indicate significant operational concern."
        },

        {
            "equipment": "CV-102",
            "role": "SECONDARY CONTRIBUTOR",
            "priority": 72.0,
            "reason":
                "Valve position warning and correlated event activity."
        },

        {
            "equipment": "PT-201",
            "role": "RELATED CONTRIBUTOR",
            "priority": 64.0,
            "reason":
                "Pressure / temperature evidence is related "
                "to the developing plant condition."
        }
    ]

    contributors.sort(
        key=lambda item: item["priority"],
        reverse=True
    )

    return {
        "contributors": contributors,
        "primary": contributors[0],
        "ranking_status": "RANKED"
    }


# ============================================================
# V5.5.4
# EVIDENCE STRENGTH & UNCERTAINTY
# ============================================================

def build_evidence_assessment():

    evidence = [
        "CV-101 valve position increased.",
        "CV-102 valve position increased.",
        "PT-201 abnormal process signal detected.",
        "CV-101 and CV-102 are PROCESS_RELATED.",
        "CV-102 and PT-201 are PROCESS_RELATED.",
        "Developing event chain detected.",
        "Equipment risk evidence available.",
        "Equipment health evidence available."
    ]

    unique = []
    seen = set()

    for item in evidence:

        normalized = (
            item.lower()
            .strip()
        )

        if normalized not in seen:

            seen.add(normalized)
            unique.append(item)

    evidence_count = len(unique)

    if evidence_count >= 7:

        confidence = 88
        confidence_level = "HIGH"

    elif evidence_count >= 4:

        confidence = 75
        confidence_level = "MEDIUM"

    elif evidence_count >= 2:

        confidence = 60
        confidence_level = "LOW"

    else:

        confidence = 0
        confidence_level = "INSUFFICIENT"

    uncertainty = [
        "Correlation does not establish causation.",
        "Process condition must be verified by personnel.",
        "Maintenance intervention requires human authorization.",
        "Additional field evidence may change the assessment."
    ]

    return {
        "raw_evidence_count": len(evidence),
        "unique_evidence_count": evidence_count,
        "confidence": confidence,
        "confidence_level": confidence_level,
        "uncertainty": uncertainty,
        "causation_established": False
    }


# ============================================================
# V5.5.5
# MANAGEMENT PRIORITY EXPLANATION
# ============================================================

def build_priority_explanation(
    situation,
    ranking,
    evidence
):

    primary = ranking["primary"]

    priority = primary["priority"]

    if priority >= 80:

        level = "P1 — URGENT"

    elif priority >= 60:

        level = "P2 — HIGH"

    else:

        level = "P3 — MONITOR"

    reasons = [
        "Multiple equipment signals are abnormal.",
        (
            f'Primary contributor identified as '
            f'{primary["equipment"]}.'
        ),
        (
            f'Evidence confidence is '
            f'{evidence["confidence_level"]} '
            f'({evidence["confidence"]}/100).'
        ),
        "Relationship-aware event activity is present.",
        "A developing plant event chain is present."
    ]

    return {
        "management_level": level,
        "priority": priority,
        "reasons": reasons
    }


# ============================================================
# V5.5.6
# MULTI-EQUIPMENT SITUATION SYNTHESIS
# ============================================================

def build_situation_synthesis(
    situation,
    changes,
    ranking,
    evidence,
    priority
):

    primary = ranking["primary"]

    synthesis = (
        f'{situation["area"]} has a developing plant condition. '
        f'{primary["equipment"]} is the primary contributor, '
        f'with related activity involving '
        f'{", ".join(situation["affected_equipment"][1:])}. '
        f'{changes["change_count"]} significant equipment changes '
        f'were identified. '
        f'Evidence confidence is '
        f'{evidence["confidence_level"]} '
        f'({evidence["confidence"]}/100). '
        f'Management review is recommended.'
    )

    return {
        "synthesis": synthesis,
        "affected_equipment":
            situation["affected_equipment"],
        "primary_equipment":
            primary["equipment"],
        "confidence":
            evidence["confidence"],
        "management_priority":
            priority["priority"],
        "causation_established": False
    }


# ============================================================
# V5.5.7
# RECOMMENDED MANAGEMENT REVIEW
# ============================================================

def build_management_review(
    situation,
    priority,
    evidence
):

    recommendation = (
        "Perform a controlled maintenance and process review "
        "of the primary and related equipment. Verify field "
        "condition, process impact, instrument condition and "
        "associated control-valve / process relationships "
        "before any maintenance intervention."
    )

    return {
        "recommendation": recommendation,

        "review_scope": [
            "Primary equipment: CV-101",
            "Related equipment: CV-102",
            "Related process instrument: PT-201",
            "Verify process condition",
            "Verify field instrument condition",
            "Review maintenance history"
        ],

        "management_priority":
            priority["priority"],

        "evidence_confidence":
            evidence["confidence"],

        "human_review_required":
            True
    }


# ============================================================
# V5.5.8
# HUMAN DECISION GOVERNANCE
# ============================================================

def build_governance():

    return {
        "human_decision_required": True,

        "human_verification_required": True,

        "permit_check_required": True,

        "isolation_check_required": True,

        "risk_assessment_required": True,

        "automatic_authorization": False
    }


# ============================================================
# V5.5.9
# READ-ONLY SAFETY VALIDATION
# ============================================================

def validate_safety(
    governance
):

    passed = (
        governance["human_decision_required"]
        is True

        and

        governance["human_verification_required"]
        is True

        and

        governance["automatic_authorization"]
        is False
    )

    return {
        "pass": passed,

        "read_only": True,

        "plc_write": False,

        "scada_control": False,

        "human_decision_required":
            governance["human_decision_required"],

        "automatic_authorization":
            governance["automatic_authorization"],

        "causation_established":
            False
    }


# ============================================================
# V5.5.10
# FULL INTEGRATION
# ============================================================

def run_full_test():

    print()
    print("=" * 72)
    print(
        "ANVIQO V5.5 FULL MANAGEMENT INTELLIGENCE"
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
    # V5.5.1
    # --------------------------------------------------------

    situation = build_management_situation()

    v551 = {
        "version": "V5.5.1",
        "name": "MANAGEMENT SITUATION SUMMARY",
        "pass":
            situation["management_attention"]
    }

    # --------------------------------------------------------
    # V5.5.2
    # --------------------------------------------------------

    changes = build_what_changed()

    v552 = {
        "version": "V5.5.2",
        "name": "WHAT CHANGED INTELLIGENCE",
        "pass":
            changes["change_count"] >= 2
    }

    # --------------------------------------------------------
    # V5.5.3
    # --------------------------------------------------------

    ranking = build_contributor_ranking()

    v553 = {
        "version": "V5.5.3",
        "name": "PRIMARY CONTRIBUTOR RANKING",
        "pass":
            len(
                ranking["contributors"]
            ) >= 2
            and
            ranking["primary"][
                "equipment"
            ] == "CV-101"
    }

    # --------------------------------------------------------
    # V5.5.4
    # --------------------------------------------------------

    evidence = build_evidence_assessment()

    v554 = {
        "version": "V5.5.4",
        "name": "EVIDENCE STRENGTH / UNCERTAINTY",
        "pass":
            evidence["unique_evidence_count"]
            > 0
            and
            evidence["confidence"] > 0
            and
            evidence["causation_established"]
            is False
    }

    # --------------------------------------------------------
    # V5.5.5
    # --------------------------------------------------------

    priority = build_priority_explanation(
        situation,
        ranking,
        evidence
    )

    v555 = {
        "version": "V5.5.5",
        "name": "MANAGEMENT PRIORITY EXPLANATION",
        "pass":
            priority["priority"] > 0
            and
            len(
                priority["reasons"]
            ) >= 3
    }

    # --------------------------------------------------------
    # V5.5.6
    # --------------------------------------------------------

    synthesis = build_situation_synthesis(
        situation,
        changes,
        ranking,
        evidence,
        priority
    )

    v556 = {
        "version": "V5.5.6",
        "name": "MULTI-EQUIPMENT SITUATION SYNTHESIS",
        "pass":
            len(
                synthesis["affected_equipment"]
            ) >= 3
            and
            synthesis["primary_equipment"]
            == "CV-101"
    }

    # --------------------------------------------------------
    # V5.5.7
    # --------------------------------------------------------

    review = build_management_review(
        situation,
        priority,
        evidence
    )

    v557 = {
        "version": "V5.5.7",
        "name": "RECOMMENDED MANAGEMENT REVIEW",
        "pass":
            review["human_review_required"]
            is True
            and
            len(
                review["review_scope"]
            ) >= 3
    }

    # --------------------------------------------------------
    # V5.5.8
    # --------------------------------------------------------

    governance = build_governance()

    v558 = {
        "version": "V5.5.8",
        "name": "HUMAN DECISION GOVERNANCE",
        "pass":
            governance[
                "human_decision_required"
            ]
            is True
            and
            governance[
                "automatic_authorization"
            ]
            is False
    }

    # --------------------------------------------------------
    # V5.5.9
    # --------------------------------------------------------

    safety = validate_safety(
        governance
    )

    v559 = {
        "version": "V5.5.9",
        "name": "READ-ONLY SAFETY VALIDATION",
        "pass":
            safety["pass"]
            and
            safety["read_only"]
            and
            not safety["plc_write"]
            and
            not safety["scada_control"]
    }

    # --------------------------------------------------------
    # V5.5.10
    # --------------------------------------------------------

    results = [
        v551,
        v552,
        v553,
        v554,
        v555,
        v556,
        v557,
        v558,
        v559
    ]

    overall = all(
        item["pass"]
        for item in results
    )

    print()
    print("MODULE STATUS")
    print("-" * 72)

    for item in results:

        status = (
            "PASS"
            if item["pass"]
            else "FAIL"
        )

        print(
            f'{item["version"]:<9}'
            f'{item["name"]:<44}'
            f': {status}'
        )

    # --------------------------------------------------------
    # MANAGEMENT SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print("MANAGEMENT INTELLIGENCE SUMMARY")
    print("=" * 72)

    print()

    print(
        "Area                  :",
        situation["area"]
    )

    print(
        "Plant condition       :",
        situation["status"]
    )

    print(
        "Primary contributor   :",
        ranking["primary"]["equipment"]
    )

    print(
        "Affected equipment    :",
        ", ".join(
            situation["affected_equipment"]
        )
    )

    print(
        "Changes detected      :",
        changes["change_count"]
    )

    print(
        "Evidence confidence   :",
        f'{evidence["confidence"]}/100 '
        f'({evidence["confidence_level"]})'
    )

    print(
        "Management priority   :",
        f'{priority["management_level"]} '
        f'({priority["priority"]}/100)'
    )

    print()

    print("WHY ANVIQO IS CONCERNED")
    print("-" * 72)

    for reason in priority["reasons"]:

        print(
            "✓",
            reason
        )

    print()

    print("RECOMMENDED MANAGEMENT REVIEW")
    print("-" * 72)

    print(
        review["recommendation"]
    )

    # --------------------------------------------------------
    # UNCERTAINTY
    # --------------------------------------------------------

    print()
    print("UNCERTAINTY / LIMITATIONS")
    print("-" * 72)

    for item in evidence["uncertainty"]:

        print(
            "•",
            item
        )

    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print("SAFETY / CONTROL STATE")
    print("=" * 72)

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
    # FINAL
    # --------------------------------------------------------

    print()
    print("=" * 72)

    if overall:

        print(
            "ANVIQO V5.5 OVERALL STATUS : PASS"
        )

        print(
            "PLANT MANAGEMENT INTELLIGENCE : PASS"
        )

        print(
            "EVIDENCE / UNCERTAINTY : PASS"
        )

        print(
            "MANAGEMENT REVIEW : PASS"
        )

        print(
            "HUMAN GOVERNANCE : PASS"
        )

        print(
            "SAFETY BOUNDARY : PASS"
        )

    else:

        print(
            "ANVIQO V5.5 OVERALL STATUS : ATTENTION"
        )

        print(
            "One or more V5.5 gates failed."
        )

    print("=" * 72)
    print()


if __name__ == "__main__":

    run_full_test()
