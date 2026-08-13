"""
ANVIQO V5.3.12
Management Decision Validation & Governance

Purpose:
Validate the V5.3.11 management decision before it reaches human review.

Safety:
- Read-only validation
- No PLC writes
- No SCADA writes
- No automatic maintenance authorization
- Human decision remains mandatory
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ValidationResult:
    name: str
    status: str
    detail: str


class ManagementDecisionValidator:
    """
    V5.3.12 governance validator.

    Validates:
    1. Priority
    2. Evidence
    3. Learning
    4. Confidence
    5. Recommendation
    6. Safety
    7. Human authorization
    8. Control boundary
    9. Auditability
    """

    def __init__(self, report):
        self.report = report
        self.results: List[ValidationResult] = []

    def add_result(self, name, status, detail):
        self.results.append(
            ValidationResult(
                name=name,
                status=status,
                detail=detail
            )
        )

    # ---------------------------------------------------------
    # 1. PRIORITY VALIDATION
    # ---------------------------------------------------------

    def validate_priority(self):
        priority = self.report.get("priority", 0)
        level = self.report.get("priority_level", "")

        if priority >= 80 and level == "P1 — URGENT":
            self.add_result(
                "Priority validation",
                "PASS",
                f"P1 priority is supported by priority score {priority}/100."
            )
        else:
            self.add_result(
                "Priority validation",
                "ATTENTION",
                "Priority level and score require review."
            )

    # ---------------------------------------------------------
    # 2. EVIDENCE VALIDATION
    # ---------------------------------------------------------

    def validate_evidence(self):
        evidence = self.report.get("evidence", [])

        if evidence and len(evidence) > 0:
            self.add_result(
                "Evidence traceability",
                "PASS",
                f"{len(evidence)} evidence item(s) available."
            )
        else:
            self.add_result(
                "Evidence traceability",
                "FAIL",
                "No supporting evidence was supplied."
            )

    # ---------------------------------------------------------
    # 3. LEARNING VALIDATION
    # ---------------------------------------------------------

    def validate_learning(self):
        learning_supported = self.report.get(
            "learning_supported",
            False
        )

        if learning_supported:
            self.add_result(
                "Learning validation",
                "PASS",
                "Verified plant experience supports the decision."
            )
        else:
            self.add_result(
                "Learning validation",
                "ATTENTION",
                "No verified learning support was found."
            )

    # ---------------------------------------------------------
    # 4. CONFIDENCE VALIDATION
    # ---------------------------------------------------------

    def validate_confidence(self):
        confidence = self.report.get(
            "confidence_score",
            0
        )

        if confidence >= 80:
            self.add_result(
                "Confidence validation",
                "PASS",
                f"Historical experience confidence is HIGH ({confidence}/100)."
            )
        elif confidence >= 60:
            self.add_result(
                "Confidence validation",
                "ATTENTION",
                f"Confidence is moderate ({confidence}/100)."
            )
        else:
            self.add_result(
                "Confidence validation",
                "FAIL",
                f"Confidence is insufficient ({confidence}/100)."
            )

    # ---------------------------------------------------------
    # 5. RECOMMENDATION VALIDATION
    # ---------------------------------------------------------

    def validate_recommendation(self):
        decision = self.report.get(
            "decision",
            ""
        )

        recommendation = self.report.get(
            "recommendation",
            ""
        )

        if decision and recommendation:
            self.add_result(
                "Recommendation validation",
                "PASS",
                "Management decision has a corresponding recommended action."
            )
        else:
            self.add_result(
                "Recommendation validation",
                "FAIL",
                "Decision or recommended action is missing."
            )

    # ---------------------------------------------------------
    # 6. SAFETY VALIDATION
    # ---------------------------------------------------------

    def validate_safety(self):
        safety = self.report.get(
            "safety",
            {}
        )

        required_checks = [
            "human_verification",
            "permit_check",
            "isolation_check",
            "risk_assessment"
        ]

        failed = []

        for check in required_checks:
            if not safety.get(check, False):
                failed.append(check)

        if not failed:
            self.add_result(
                "Safety validation",
                "PASS",
                "Human verification, permit, isolation and risk assessment checks passed."
            )
        else:
            self.add_result(
                "Safety validation",
                "FAIL",
                "Safety checks failed: " + ", ".join(failed)
            )

    # ---------------------------------------------------------
    # 7. HUMAN AUTHORIZATION
    # ---------------------------------------------------------

    def validate_human_authorization(self):
        authorization = self.report.get(
            "human_authorization_required",
            True
        )

        if authorization:
            self.add_result(
                "Human authorization",
                "PASS",
                "Human authorization remains mandatory."
            )
        else:
            self.add_result(
                "Human authorization",
                "FAIL",
                "Human authorization requirement is missing."
            )

    # ---------------------------------------------------------
    # 8. CONTROL BOUNDARY
    # ---------------------------------------------------------

    def validate_control_boundary(self):
        read_only = self.report.get(
            "read_only",
            True
        )

        plc_write = self.report.get(
            "plc_write",
            False
        )

        scada_write = self.report.get(
            "scada_write",
            False
        )

        if read_only and not plc_write and not scada_write:
            self.add_result(
                "Control boundary",
                "PASS",
                "Anviqo remains read-only with PLC and SCADA writes disabled."
            )
        else:
            self.add_result(
                "Control boundary",
                "FAIL",
                "Unsafe control capability detected."
            )

    # ---------------------------------------------------------
    # 9. AUDITABILITY
    # ---------------------------------------------------------

    def validate_auditability(self):
        decision = self.report.get("decision", "")
        evidence = self.report.get("evidence", [])
        recommendation = self.report.get("recommendation", "")

        if decision and evidence and recommendation:
            self.add_result(
                "Auditability",
                "PASS",
                "Decision, evidence and recommendation are traceable."
            )
        else:
            self.add_result(
                "Auditability",
                "FAIL",
                "Decision audit trail is incomplete."
            )

    # ---------------------------------------------------------
    # RUN VALIDATION
    # ---------------------------------------------------------

    def validate(self):

        self.results = []

        self.validate_priority()
        self.validate_evidence()
        self.validate_learning()
        self.validate_confidence()
        self.validate_recommendation()
        self.validate_safety()
        self.validate_human_authorization()
        self.validate_control_boundary()
        self.validate_auditability()

        failures = [
            result
            for result in self.results
            if result.status == "FAIL"
        ]

        if failures:
            overall = "GOVERNANCE REVIEW REQUIRED"
        else:
            overall = "APPROVED FOR HUMAN REVIEW"

        return overall, self.results


# =============================================================
# V5.3.12 TEST DATA
# =============================================================

def build_test_report():
    """
    Test representation of the V5.3.11 CV-101 management report.
    """

    return {
        "equipment": "CV-101 | MBF",

        "priority_level": "P1 — URGENT",
        "priority": 84.7,

        "decision": "MAINTENANCE REVIEW REQUIRED",

        "evidence": [
            "Valve position is increasing significantly with worsening operational trend.",
            "High operational priority detected.",
            "Verified maintenance history supports intervention."
        ],

        "learning_supported": True,

        "confidence_score": 88,

        "recommendation": (
            "Perform a controlled maintenance review of CV-101 "
            "and verify the associated process condition."
        ),

        "human_authorization_required": True,

        "safety": {
            "human_verification": True,
            "permit_check": True,
            "isolation_check": True,
            "risk_assessment": True
        },

        "read_only": True,
        "plc_write": False,
        "scada_write": False
    }


# =============================================================
# TEST RUNNER
# =============================================================

def run_v5312_test():

    report = build_test_report()

    validator = ManagementDecisionValidator(report)

    overall, results = validator.validate()

    print("=" * 68)
    print("ANVIQO V5.3.12 MANAGEMENT DECISION VALIDATION")
    print("=" * 68)

    print()
    print("EQUIPMENT")
    print("-" * 68)
    print(report["equipment"])

    print()
    print("VALIDATION RESULTS")
    print("-" * 68)

    for result in results:
        print(f"{result.name:<28} : {result.status}")
        print(f"  {result.detail}")

    print()
    print("MANAGEMENT DECISION")
    print("-" * 68)
    print(f"Decision                  : {report['decision']}")
    print(f"Priority                  : {report['priority_level']}")
    print(f"Priority score            : {report['priority']}/100")

    print()
    print("GOVERNANCE STATUS")
    print("-" * 68)
    print(f"Overall status            : {overall}")

    print()
    print("SAFETY BOUNDARY")
    print("-" * 68)
    print("Human authorization       : REQUIRED")
    print("Read-only                 : True")
    print("PLC write                 : False")
    print("SCADA write               : False")

    print()
    print("=" * 68)

    if overall == "APPROVED FOR HUMAN REVIEW":
        print("V5.3.12 MODULE TEST: PASS")
        print("MANAGEMENT DECISION GOVERNANCE: PASS")
    else:
        print("V5.3.12 MODULE TEST: ATTENTION REQUIRED")
        print("MANAGEMENT DECISION GOVERNANCE: REVIEW REQUIRED")

    print("=" * 68)


if __name__ == "__main__":
    run_v5312_test()
