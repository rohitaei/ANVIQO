"""
ANVIQO V5.4.5
Evidence Deduplication & Confidence Integrity

Purpose:
    Remove duplicate evidence before confidence calculation.

Safety:
    Read-only
    No PLC writes
    No SCADA writes
    No automatic control
"""


class EvidenceIntegrityEngine:

    def __init__(self):
        self.raw_evidence = []

    # ---------------------------------------------------------
    # ADD EVIDENCE
    # ---------------------------------------------------------

    def add_evidence(self, evidence):

        if evidence:
            self.raw_evidence.append(
                str(evidence).strip()
            )

    # ---------------------------------------------------------
    # DEDUPLICATE
    # ---------------------------------------------------------

    def unique_evidence(self):

        unique = []
        seen = set()

        for item in self.raw_evidence:

            normalized = (
                item.lower()
                .strip()
            )

            if normalized not in seen:

                seen.add(normalized)
                unique.append(item)

        return unique

    # ---------------------------------------------------------
    # CONFIDENCE INTEGRITY
    # ---------------------------------------------------------

    def calculate_confidence(
        self,
        source_count,
        unique_evidence_count
    ):

        if source_count >= 3:
            base = 85

        elif source_count == 2:
            base = 75

        elif source_count == 1:
            base = 60

        else:
            base = 0

        # Evidence quantity can strengthen confidence,
        # but duplicates cannot.
        if unique_evidence_count >= 8:
            base += 3

        elif unique_evidence_count >= 5:
            base += 2

        elif unique_evidence_count >= 3:
            base += 1

        return min(base, 95)

    # ---------------------------------------------------------
    # BUILD RESULT
    # ---------------------------------------------------------

    def analyze(self, source_count):

        unique = self.unique_evidence()

        raw_count = len(
            self.raw_evidence
        )

        unique_count = len(unique)

        duplicate_count = (
            raw_count - unique_count
        )

        confidence = self.calculate_confidence(
            source_count,
            unique_count
        )

        if confidence >= 80:
            confidence_level = "HIGH"

        elif confidence >= 65:
            confidence_level = "MEDIUM"

        elif confidence >= 50:
            confidence_level = "LOW"

        else:
            confidence_level = "INSUFFICIENT"

        return {
            "raw_evidence_count": raw_count,
            "unique_evidence_count": unique_count,
            "duplicate_evidence_count": duplicate_count,
            "unique_evidence": unique,
            "confidence": confidence,
            "confidence_level": confidence_level,
            "read_only": True,
            "plc_write": False,
            "scada_write": False
        }


# =============================================================
# TEST
# =============================================================

def run_test():

    engine = EvidenceIntegrityEngine()

    # ---------------------------------------------------------
    # Deliberately duplicated evidence
    # ---------------------------------------------------------

    test_evidence = [

        "Plant Brain identified equipment-level risk and health evidence.",

        "Primary equipment contributor: CV-101.",

        "Relationship-aware correlation detected between CV-101 and CV-102.",

        "Relationship type: PROCESS_RELATED.",

        "Relationship-aware correlation detected between CV-101 and CV-102.",

        "Relationship type: PROCESS_RELATED.",

        "Relationship-aware correlation detected between CV-102 and PT-201.",

        "Relationship type: PROCESS_RELATED.",

        "Relationship-aware correlation detected between CV-102 and PT-201.",

        "Relationship type: PROCESS_RELATED.",

        "Plant event chain detected across CV-101 and CV-102.",

        "Event chain status: DEVELOPING EVENT CHAIN.",

        "Plant event chain detected across CV-102 and PT-201.",

        "Event chain status: DEVELOPING EVENT CHAIN."
    ]

    for evidence in test_evidence:

        engine.add_evidence(
            evidence
        )

    result = engine.analyze(
        source_count=3
    )

    print("=" * 72)
    print("ANVIQO V5.4.5 EVIDENCE INTEGRITY")
    print("=" * 72)

    print()

    print("RAW EVIDENCE COUNT")
    print("-" * 72)

    print(
        result["raw_evidence_count"]
    )

    print()

    print("UNIQUE EVIDENCE COUNT")
    print("-" * 72)

    print(
        result["unique_evidence_count"]
    )

    print()

    print("DUPLICATE EVIDENCE REMOVED")
    print("-" * 72)

    print(
        result["duplicate_evidence_count"]
    )

    print()

    print("UNIQUE EVIDENCE")
    print("-" * 72)

    for item in result[
        "unique_evidence"
    ]:

        print(
            "✓ " + item
        )

    print()

    print("CONFIDENCE")
    print("-" * 72)

    print(
        f"{result['confidence']}/100 "
        f"({result['confidence_level']})"
    )

    print()

    print("SAFETY / CONTROL BOUNDARY")
    print("-" * 72)

    print(
        "Read-only   : "
        f"{result['read_only']}"
    )

    print(
        "PLC write   : "
        f"{result['plc_write']}"
    )

    print(
        "SCADA write : "
        f"{result['scada_write']}"
    )

    print()
    print("=" * 72)

    if (
        result["duplicate_evidence_count"] > 0
        and
        result["unique_evidence_count"]
        < result["raw_evidence_count"]
        and
        result["confidence"] > 0
        and
        result["read_only"]
        and
        not result["plc_write"]
        and
        not result["scada_write"]
    ):

        print(
            "V5.4.5 MODULE TEST: PASS"
        )

        print(
            "EVIDENCE DEDUPLICATION: PASS"
        )

        print(
            "CONFIDENCE INTEGRITY: PASS"
        )

        print(
            "SAFETY BOUNDARY: PASS"
        )

    else:

        print(
            "V5.4.5 MODULE TEST: FAIL"
        )

    print("=" * 72)


if __name__ == "__main__":
    run_test()
