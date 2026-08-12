"""
ANVIQO V5.6
PLANT DECISION INTELLIGENCE

Decision-support layer built above V5.5.

V5.6.1  Decision Situation
V5.6.2  Decision Alternatives
V5.6.3  Priority Comparison
V5.6.4  Risk / Impact Assessment
V5.6.5  Evidence Trade-off
V5.6.6  Decision Recommendation
V5.6.7  Confidence / Uncertainty
V5.6.8  Human Decision Gate
V5.6.9  Safety / Control Boundary
V5.6.10 Full V5.6 Integration

IMPORTANT:
    Recommendation only.
    No automatic authorization.
    No PLC write.
    No SCADA control.
    No automatic maintenance execution.
    No causation claim.
"""

from datetime import datetime


# ============================================================
# V5.6.1
# DECISION SITUATION
# ============================================================

def build_decision_situation():

    return {
        "area": "MBF",

        "primary_equipment": "CV-101",

        "related_equipment": [
            "CV-102",
            "PT-201"
        ],

        "plant_condition":
            "Developing correlated equipment condition.",

        "management_priority": 84.7,

        "decision_required": True
    }


# ============================================================
# V5.6.2
# DECISION ALTERNATIVES
# ============================================================

def build_decision_alternatives():

    return [
        {
            "id": "A1",
            "name": "Immediate controlled maintenance review",

            "description":
                "Review CV-101 condition, verify process impact "
                "and prepare controlled maintenance intervention.",

            "priority": 1,

            "benefit":
                "Addresses the highest-priority equipment concern.",

            "risk":
                "Maintenance activity may affect process operation "
                "if not properly planned.",

            "requires_human":
                True
        },

        {
            "id": "A2",
            "name": "Enhanced operational monitoring",

            "description":
                "Continue close monitoring of CV-101, CV-102 and "
                "PT-201 while collecting additional evidence.",

            "priority": 2,

            "benefit":
                "Allows additional evidence to be collected "
                "without immediate intervention.",

            "risk":
                "Existing condition may continue to deteriorate.",

            "requires_human":
                True
        },

        {
            "id": "A3",
            "name": "Routine monitoring",

            "description":
                "Return equipment to normal monitoring frequency.",

            "priority": 3,

            "benefit":
                "Lowest immediate operational disruption.",

            "risk":
                "May under-react to an active developing condition.",

            "requires_human":
                True
        }
    ]


# ============================================================
# V5.6.3
# PRIORITY COMPARISON
# ============================================================

def compare_priorities(
    situation,
    alternatives
):

    primary_priority = situation[
        "management_priority"
    ]

    comparison = []

    for alternative in alternatives:

        if alternative["id"] == "A1":

            score = primary_priority

        elif alternative["id"] == "A2":

            score = primary_priority - 12

        else:

            score = primary_priority - 30

        comparison.append({
            "id": alternative["id"],
            "name": alternative["name"],
            "decision_score": round(
                max(score, 0),
                1
            )
        })

    comparison.sort(
        key=lambda item:
            item["decision_score"],
        reverse=True
    )

    return {
        "comparison": comparison,
        "preferred":
            comparison[0],
        "status":
            "PRIORITY COMPARISON COMPLETE"
    }


# ============================================================
# V5.6.4
# RISK / IMPACT ASSESSMENT
# ============================================================

def build_risk_impact():

    return {
        "operational_risk": "HIGH",

        "maintenance_risk":
            "CONTROLLED / MANAGEABLE",

        "process_impact":
            "REQUIRES VERIFICATION",

        "equipment_deterioration_risk":
            "PRESENT",

        "decision_risk":
            "HUMAN REVIEW REQUIRED",

        "automatic_execution":
            False
    }


# ============================================================
# V5.6.5
# EVIDENCE TRADE-OFF
# ============================================================

def build_evidence_tradeoff():

    supporting_evidence = [
        "CV-101 valve position increased.",
        "CV-102 valve position increased.",
        "PT-201 abnormal process evidence detected.",
        "Relationship-aware correlation exists.",
        "Developing event chain exists.",
        "Equipment risk evidence is available.",
        "Equipment health evidence is available.",
        "Verified maintenance experience supports review."
    ]

    limiting_evidence = [
        "Correlation does not establish causation.",
        "Field condition has not been independently verified.",
        "Process impact requires human confirmation.",
        "Additional evidence may change the recommendation."
    ]

    return {
        "supporting_evidence":
            supporting_evidence,

        "limiting_evidence":
            limiting_evidence,

        "evidence_balance":
            "SUPPORTS CONTROLLED REVIEW",

        "causation_established":
            False
    }


# ============================================================
# V5.6.6
# DECISION RECOMMENDATION
# ============================================================

def build_decision_recommendation(
    situation,
    priority,
    risk,
    evidence
):

    preferred = priority["preferred"]

    recommendation = (
        "ANVIQO recommends a controlled maintenance review "
        "of CV-101 with verification of associated process "
        "conditions and related equipment CV-102 and PT-201. "
        "The recommendation is based on the combined evidence "
        "and priority assessment, not on an automatic causation "
        "claim."
    )

    return {
        "preferred_option":
            preferred["name"],

        "preferred_option_id":
            preferred["id"],

        "recommendation":
            recommendation,

        "decision_basis": [
            "Highest-priority equipment contributor.",
            "Multiple related equipment signals.",
            "Developing event chain.",
            "Evidence supports controlled review.",
            "Operational risk requires attention."
        ],

        "automatic_action":
            False
    }


# ============================================================
# V5.6.7
# CONFIDENCE / UNCERTAINTY
# ============================================================

def build_decision_confidence(
    evidence
):

    supporting_count = len(
        evidence["supporting_evidence"]
    )

    limiting_count = len(
        evidence["limiting_evidence"]
    )

    raw_score = (
        supporting_count * 12
        -
        limiting_count * 3
    )

    confidence_score = min(
        max(raw_score, 0),
        100
    )

    if confidence_score >= 80:

        level = "HIGH"

    elif confidence_score >= 60:

        level = "MEDIUM"

    else:

        level = "LOW"

    return {
        "confidence_score":
            confidence_score,

        "confidence_level":
            level,

        "uncertainty_present":
            limiting_count > 0,

        "causation_claim":
            False
    }


# ============================================================
# V5.6.8
# HUMAN DECISION GATE
# ============================================================

def build_human_decision_gate():

    return {
        "human_decision_required":
            True,

        "human_verification_required":
            True,

        "permit_check_required":
            True,

        "isolation_check_required":
            True,

        "risk_assessment_required":
            True,

        "automatic_authorization":
            False,

        "automatic_execution":
            False
    }


# ============================================================
# V5.6.9
# SAFETY / CONTROL BOUNDARY
# ============================================================

def validate_control_boundary(
    governance
):

    human_required = (
        governance[
            "human_decision_required"
        ]
        is True
    )

    authorization_blocked = (
        governance[
            "automatic_authorization"
        ]
        is False
    )

    execution_blocked = (
        governance[
            "automatic_execution"
        ]
        is False
    )

    return {
        "pass":
            (
                human_required
                and
                authorization_blocked
                and
                execution_blocked
            ),

        "read_only":
            True,

        "plc_write":
            False,

        "scada_control":
            False,

        "human_decision_required":
            human_required,

        "automatic_authorization":
            False,

        "automatic_execution":
            False,

        "causation_claim":
            False
    }


# ============================================================
# V5.6.10
# FULL INTEGRATION TEST
# ============================================================

def run_full_test():

    print()
    print("=" * 72)
    print(
        "ANVIQO V5.6 FULL DECISION INTELLIGENCE VALIDATION"
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
    # V5.6.1
    # --------------------------------------------------------

    situation = build_decision_situation()

    v561 = {
        "version": "V5.6.1",
        "name": "DECISION SITUATION",
        "pass":
            situation["decision_required"]
    }

    # --------------------------------------------------------
    # V5.6.2
    # --------------------------------------------------------

    alternatives = build_decision_alternatives()

    v562 = {
        "version": "V5.6.2",
        "name": "DECISION ALTERNATIVES",
        "pass":
            len(alternatives) >= 3
            and
            all(
                item["requires_human"]
                for item in alternatives
            )
    }

    # --------------------------------------------------------
    # V5.6.3
    # --------------------------------------------------------

    priority = compare_priorities(
        situation,
        alternatives
    )

    v563 = {
        "version": "V5.6.3",
        "name": "PRIORITY COMPARISON",
        "pass":
            priority["preferred"]["id"]
            == "A1"
    }

    # --------------------------------------------------------
    # V5.6.4
    # --------------------------------------------------------

    risk = build_risk_impact()

    v564 = {
        "version": "V5.6.4",
        "name": "RISK / IMPACT ASSESSMENT",
        "pass":
            risk["operational_risk"]
            == "HIGH"
            and
            risk["automatic_execution"]
            is False
    }

    # --------------------------------------------------------
    # V5.6.5
    # --------------------------------------------------------

    evidence = build_evidence_tradeoff()

    v565 = {
        "version": "V5.6.5",
        "name": "EVIDENCE TRADE-OFF",
        "pass":
            len(
                evidence[
                    "supporting_evidence"
                ]
            ) >= 5

            and

            len(
                evidence[
                    "limiting_evidence"
                ]
            ) >= 2

            and

            evidence[
                "causation_established"
            ]
            is False
    }

    # --------------------------------------------------------
    # V5.6.6
    # --------------------------------------------------------

    recommendation = build_decision_recommendation(
        situation,
        priority,
        risk,
        evidence
    )

    v566 = {
        "version": "V5.6.6",
        "name": "DECISION RECOMMENDATION",
        "pass":
            recommendation[
                "preferred_option_id"
            ]
            == "A1"

            and

            recommendation[
                "automatic_action"
            ]
            is False
    }

    # --------------------------------------------------------
    # V5.6.7
    # --------------------------------------------------------

    confidence = build_decision_confidence(
        evidence
    )

    v567 = {
        "version": "V5.6.7",
        "name": "CONFIDENCE / UNCERTAINTY",
        "pass":
            confidence[
                "confidence_score"
            ] > 0

            and

            confidence[
                "uncertainty_present"
            ]

            and

            confidence[
                "causation_claim"
            ]
            is False
    }

    # --------------------------------------------------------
    # V5.6.8
    # --------------------------------------------------------

    governance = build_human_decision_gate()

    v568 = {
        "version": "V5.6.8",
        "name": "HUMAN DECISION GATE",
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

            and

            governance[
                "automatic_execution"
            ]
            is False
    }

    # --------------------------------------------------------
    # V5.6.9
    # --------------------------------------------------------

    safety = validate_control_boundary(
        governance
    )

    v569 = {
        "version": "V5.6.9",
        "name": "SAFETY / CONTROL BOUNDARY",
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
    # RESULTS
    # --------------------------------------------------------

    results = [
        v561,
        v562,
        v563,
        v564,
        v565,
        v566,
        v567,
        v568,
        v569
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
            f'{item["name"]:<42}'
            f': {status}'
        )

    # --------------------------------------------------------
    # DECISION SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print("PLANT DECISION SUMMARY")
    print("=" * 72)

    print()

    print(
        "Area                  :",
        situation["area"]
    )

    print(
        "Primary equipment     :",
        situation["primary_equipment"]
    )

    print(
        "Related equipment     :",
        ", ".join(
            situation["related_equipment"]
        )
    )

    print(
        "Plant condition       :",
        situation["plant_condition"]
    )

    print(
        "Management priority   :",
        f'{situation["management_priority"]}/100'
    )

    print()

    print("DECISION ALTERNATIVES")
    print("-" * 72)

    for item in priority["comparison"]:

        print(
            f'{item["id"]} | '
            f'{item["name"]} | '
            f'Score {item["decision_score"]}/100'
        )

    print()

    print(
        "PREFERRED DECISION    :",
        recommendation[
            "preferred_option"
        ]
    )

    print()

    print("DECISION BASIS")
    print("-" * 72)

    for item in recommendation[
        "decision_basis"
    ]:

        print(
            "✓",
            item
        )

    print()

    print("CONFIDENCE")
    print("-" * 72)

    print(
        "Decision confidence   :",
        f'{confidence["confidence_score"]}/100'
    )

    print(
        "Confidence level      :",
        confidence["confidence_level"]
    )

    print(
        "Uncertainty present   :",
        confidence["uncertainty_present"]
    )

    print(
        "Causation claim       :",
        confidence["causation_claim"]
    )

    print()

    print("RECOMMENDED MANAGEMENT ACTION")
    print("-" * 72)

    print(
        recommendation[
            "recommendation"
        ]
    )

    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------

    print()
    print("=" * 72)
    print("FINAL SAFETY / CONTROL STATE")
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
        "AUTOMATIC EXECUTION     : FALSE"
    )

    print(
        "CAUSATION CLAIM         : FALSE"
    )

    print()
    print("=" * 72)

    if overall:

        print(
            "ANVIQO V5.6 OVERALL STATUS : PASS"
        )

        print(
            "DECISION INTELLIGENCE : PASS"
        )

        print(
            "ALTERNATIVE ANALYSIS : PASS"
        )

        print(
            "RISK / IMPACT ASSESSMENT : PASS"
        )

        print(
            "EVIDENCE TRADE-OFF : PASS"
        )

        print(
            "HUMAN DECISION GOVERNANCE : PASS"
        )

        print(
            "SAFETY BOUNDARY : PASS"
        )

    else:

        print(
            "ANVIQO V5.6 OVERALL STATUS : ATTENTION"
        )

        print(
            "One or more V5.6 gates failed."
        )

    print("=" * 72)
    print()


if __name__ == "__main__":

    run_full_test()
