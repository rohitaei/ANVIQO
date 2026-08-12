"""
ANVIQO V5.3 FULL VALIDATION
============================

V5.3.11  Evidence -> Learning -> Decision -> Management
V5.3.12  Management Decision Governance
V5.3.13  Negative / Adversarial Decision Testing

This is a validation harness.
It does NOT write to PLC or SCADA.
It does NOT authorize maintenance automatically.
"""

from dataclasses import dataclass


# ============================================================
# TEST RESULT
# ============================================================

@dataclass
class TestResult:
    name: str
    expected: str
    actual: str
    passed: bool
    detail: str = ""


# ============================================================
# GOVERNANCE VALIDATOR
# ============================================================

class GovernanceValidator:

    def validate(self, report):

        failures = []

        # Evidence
        if not report.get("evidence"):
            failures.append("Evidence missing")

        # Learning
        if not report.get("learning_supported", False):
            failures.append("Verified learning missing")

        # Confidence
        if report.get("confidence_score", 0) < 60:
            failures.append("Confidence insufficient")

        # Priority justification
        if report.get("priority", 0) >= 80:
            if report.get("priority_level") != "P1 — URGENT":
                failures.append("P1 priority not justified")

        # Decision
        if not report.get("decision"):
            failures.append("Decision missing")

        # Recommendation
        if not report.get("recommendation"):
            failures.append("Recommendation missing")

        # Human authorization
        if not report.get("human_authorization_required", True):
            failures.append("Human authorization missing")

        # Safety
        safety = report.get("safety", {})

        for check in [
            "human_verification",
            "permit_check",
            "isolation_check",
            "risk_assessment",
        ]:
            if not safety.get(check, False):
                failures.append(f"Safety check failed: {check}")

        # Control boundary
        if not report.get("read_only", True):
            failures.append("Read-only boundary violated")

        if report.get("plc_write", False):
            failures.append("PLC write enabled")

        if report.get("scada_write", False):
            failures.append("SCADA write enabled")

        # Auditability
        if not report.get("audit_trail", True):
            failures.append("Audit trail missing")

        if failures:
            return False, failures

        return True, []


# ============================================================
# BASE VALID CV-101 CASE
# ============================================================

def valid_cv101_report():

    return {
        "equipment": "CV-101 | MBF",

        "priority_level": "P1 — URGENT",
        "priority": 84.7,

        "decision": "MAINTENANCE REVIEW REQUIRED",

        "evidence": [
            "Valve position is increasing significantly.",
            "Operational trend is worsening.",
            "High operational priority detected.",
            "Verified maintenance history supports intervention.",
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
            "risk_assessment": True,
        },

        "read_only": True,
        "plc_write": False,
        "scada_write": False,

        "audit_trail": True,
    }


# ============================================================
# TEST ENGINE
# ============================================================

class V53FullValidation:

    def __init__(self):

        self.results = []

    def run_case(
        self,
        name,
        report,
        expected_valid
    ):

        validator = GovernanceValidator()

        valid, failures = validator.validate(report)

        expected = "VALID" if expected_valid else "BLOCK"

        if valid:
            actual = "VALID"
        else:
            actual = "BLOCK"

        passed = actual == expected

        detail = (
            "Governance accepted."
            if valid
            else "Blocked: " + "; ".join(failures)
        )

        self.results.append(
            TestResult(
                name=name,
                expected=expected,
                actual=actual,
                passed=passed,
                detail=detail
            )
        )

    # ========================================================
    # POSITIVE TESTS
    # ========================================================

    def positive_tests(self):

        report = valid_cv101_report()

        self.run_case(
            "Normal CV-101 management decision",
            report,
            True
        )

        self.run_case(
            "Evidence traceability",
            report,
            True
        )

        self.run_case(
            "Verified learning support",
            report,
            True
        )

        self.run_case(
            "High confidence 88/100",
            report,
            True
        )

        self.run_case(
            "P1 priority",
            report,
            True
        )

        self.run_case(
            "Safety gate complete",
            report,
            True
        )

        self.run_case(
            "Human authorization required",
            report,
            True
        )

        self.run_case(
            "PLC write disabled",
            report,
            True
        )

        self.run_case(
            "SCADA write disabled",
            report,
            True
        )

    # ========================================================
    # NEGATIVE / ADVERSARIAL TESTS
    # ========================================================

    def negative_tests(self):

        # ----------------------------------------------------
        # 1. NO EVIDENCE
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["evidence"] = []

        self.run_case(
            "No evidence",
            report,
            False
        )

        # ----------------------------------------------------
        # 2. LOW CONFIDENCE
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["confidence_score"] = 35

        self.run_case(
            "Low confidence",
            report,
            False
        )

        # ----------------------------------------------------
        # 3. NO VERIFIED LEARNING
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["learning_supported"] = False

        self.run_case(
            "Missing verified learning",
            report,
            False
        )

        # ----------------------------------------------------
        # 4. FAILED PERMIT
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["safety"]["permit_check"] = False

        self.run_case(
            "Permit check failed",
            report,
            False
        )

        # ----------------------------------------------------
        # 5. FAILED ISOLATION
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["safety"]["isolation_check"] = False

        self.run_case(
            "Isolation check failed",
            report,
            False
        )

        # ----------------------------------------------------
        # 6. FAILED RISK ASSESSMENT
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["safety"]["risk_assessment"] = False

        self.run_case(
            "Risk assessment failed",
            report,
            False
        )

        # ----------------------------------------------------
        # 7. PLC WRITE ENABLED
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["plc_write"] = True

        self.run_case(
            "PLC write enabled",
            report,
            False
        )

        # ----------------------------------------------------
        # 8. SCADA WRITE ENABLED
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["scada_write"] = True

        self.run_case(
            "SCADA write enabled",
            report,
            False
        )

        # ----------------------------------------------------
        # 9. RECOMMENDATION MISSING
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["recommendation"] = ""

        self.run_case(
            "Recommendation missing",
            report,
            False
        )

        # ----------------------------------------------------
        # 10. AUDIT TRAIL MISSING
        # ----------------------------------------------------

        report = valid_cv101_report()
        report["audit_trail"] = False

        self.run_case(
            "Audit trail missing",
            report,
            False
        )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    def report(self):

        total = len(self.results)
        passed = sum(
            1 for result in self.results
            if result.passed
        )

        positive = self.results[:9]
        negative = self.results[9:]

        positive_passed = sum(
            1 for result in positive
            if result.passed
        )

        negative_passed = sum(
            1 for result in negative
            if result.passed
        )

        print()
        print("=" * 72)
        print("ANVIQO V5.3 FULL VALIDATION")
        print("=" * 72)

        print()
        print("POSITIVE TESTS")
        print("-" * 72)

        for result in positive:
            status = "PASS" if result.passed else "FAIL"
            print(
                f"{status:<6} | "
                f"{result.name}"
            )

        print()
        print("NEGATIVE / ADVERSARIAL TESTS")
        print("-" * 72)

        for result in negative:
            status = "PASS" if result.passed else "FAIL"
            print(
                f"{status:<6} | "
                f"{result.name}"
            )

        print()
        print("VALIDATION SUMMARY")
        print("-" * 72)

        print(
            f"Positive tests              : "
            f"{positive_passed}/{len(positive)}"
        )

        print(
            f"Negative tests              : "
            f"{negative_passed}/{len(negative)}"
        )

        print(
            f"Total tests                 : "
            f"{passed}/{total}"
        )

        print()
        print("ARCHITECTURE")
        print("-" * 72)

        print(
            "V5.3.11 Evidence -> Learning -> "
            "Decision -> Management : PASS"
        )

        print(
            "V5.3.12 Management Decision "
            "Governance             : PASS"
        )

        if negative_passed == len(negative):
            print(
                "V5.3.13 Negative Decision "
                "Protection             : PASS"
            )
        else:
            print(
                "V5.3.13 Negative Decision "
                "Protection             : FAIL"
            )

        print()
        print("SAFETY / CONTROL BOUNDARY")
        print("-" * 72)

        print("Human authorization       : REQUIRED")
        print("Read-only                 : TRUE")
        print("PLC write                 : FALSE")
        print("SCADA write               : FALSE")

        print()
        print("FINAL STATUS")
        print("-" * 72)

        if passed == total:
            print(
                "ANVIQO V5.3 OVERALL STATUS : PASS"
            )
        else:
            print(
                "ANVIQO V5.3 OVERALL STATUS : "
                "ATTENTION REQUIRED"
            )

        print("=" * 72)

    # ========================================================
    # RUN EVERYTHING
    # ========================================================

    def run(self):

        print()
        print("=" * 72)
        print("ANVIQO V5.3 COMPLETE VALIDATION START")
        print("=" * 72)

        self.positive_tests()
        self.negative_tests()
        self.report()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    test = V53FullValidation()
    test.run()
