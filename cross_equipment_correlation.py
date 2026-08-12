"""
ANVIQO V5.4.1
Cross-Equipment Correlation Engine

Purpose:
Correlate evidence from multiple equipment and identify
potential common operational disturbances.

Safety:
- Read-only
- No PLC writes
- No SCADA writes
- No automatic control
- Evidence-backed output
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class EquipmentSignal:
    equipment: str
    parameter: str
    value: float
    trend: str
    status: str
    area: str


@dataclass
class CorrelationResult:
    equipment_group: List[str]
    correlation_type: str
    confidence: int
    evidence: List[str]
    conclusion: str


class CrossEquipmentCorrelationEngine:

    def __init__(self):
        self.signals: List[EquipmentSignal] = []

    # ---------------------------------------------------------
    # ADD SIGNAL
    # ---------------------------------------------------------

    def add_signal(
        self,
        equipment,
        parameter,
        value,
        trend,
        status,
        area
    ):
        signal = EquipmentSignal(
            equipment=equipment,
            parameter=parameter,
            value=value,
            trend=trend,
            status=status,
            area=area
        )

        self.signals.append(signal)

    # ---------------------------------------------------------
    # GROUP BY AREA
    # ---------------------------------------------------------

    def group_by_area(self):

        groups: Dict[str, List[EquipmentSignal]] = {}

        for signal in self.signals:
            groups.setdefault(
                signal.area,
                []
            ).append(signal)

        return groups

    # ---------------------------------------------------------
    # CORRELATION ENGINE
    # ---------------------------------------------------------

    def analyze(self):

        results = []

        groups = self.group_by_area()

        for area, signals in groups.items():

            if len(signals) < 2:
                continue

            worsening = [
                signal
                for signal in signals
                if signal.trend.lower()
                in ["increasing", "worsening", "rising"]
            ]

            abnormal = [
                signal
                for signal in signals
                if signal.status.lower()
                in ["warning", "alarm", "attention", "abnormal"]
            ]

            # -------------------------------------------------
            # COMMON TREND CORRELATION
            # -------------------------------------------------

            if len(worsening) >= 2:

                equipment = [
                    signal.equipment
                    for signal in worsening
                ]

                evidence = [
                    (
                        f"{signal.equipment}: "
                        f"{signal.parameter} shows "
                        f"{signal.trend} trend."
                    )
                    for signal in worsening
                ]

                confidence = min(
                    95,
                    60 + len(worsening) * 10
                )

                results.append(
                    CorrelationResult(
                        equipment_group=equipment,
                        correlation_type="COMMON_WORSENING_TREND",
                        confidence=confidence,
                        evidence=evidence,
                        conclusion=(
                            f"{len(worsening)} equipment signals "
                            f"show a common worsening trend in "
                            f"area {area}. Potential common "
                            f"process disturbance should be reviewed."
                        )
                    )
                )

            # -------------------------------------------------
            # MULTIPLE ABNORMAL EQUIPMENT
            # -------------------------------------------------

            if len(abnormal) >= 2:

                equipment = [
                    signal.equipment
                    for signal in abnormal
                ]

                evidence = [
                    (
                        f"{signal.equipment}: "
                        f"{signal.parameter} status = "
                        f"{signal.status}."
                    )
                    for signal in abnormal
                ]

                confidence = min(
                    90,
                    55 + len(abnormal) * 10
                )

                results.append(
                    CorrelationResult(
                        equipment_group=equipment,
                        correlation_type="MULTIPLE_ABNORMAL_SIGNALS",
                        confidence=confidence,
                        evidence=evidence,
                        conclusion=(
                            f"Multiple equipment signals are "
                            f"abnormal in area {area}. "
                            f"Cross-equipment investigation "
                            f"is recommended."
                        )
                    )
                )

        return results


# =============================================================
# V5.4.1 TEST
# =============================================================

def run_test():

    engine = CrossEquipmentCorrelationEngine()

    # ---------------------------------------------------------
    # CV-101
    # ---------------------------------------------------------

    engine.add_signal(
        equipment="CV-101",
        parameter="Valve Position",
        value=78,
        trend="increasing",
        status="warning",
        area="MBF"
    )

    # ---------------------------------------------------------
    # CV-102
    # ---------------------------------------------------------

    engine.add_signal(
        equipment="CV-102",
        parameter="Valve Position",
        value=72,
        trend="increasing",
        status="warning",
        area="MBF"
    )

    # ---------------------------------------------------------
    # PT-201
    # ---------------------------------------------------------

    engine.add_signal(
        equipment="PT-201",
        parameter="Pressure",
        value=6.8,
        trend="rising",
        status="attention",
        area="MBF"
    )

    results = engine.analyze()

    print("=" * 68)
    print("ANVIQO V5.4.1 CROSS-EQUIPMENT CORRELATION")
    print("=" * 68)

    print()

    if not results:

        print("No cross-equipment correlation detected.")

    else:

        for index, result in enumerate(results, 1):

            print(
                f"CORRELATION #{index}"
            )

            print("-" * 68)

            print(
                "Equipment : "
                + ", ".join(result.equipment_group)
            )

            print(
                f"Type      : "
                f"{result.correlation_type}"
            )

            print(
                f"Confidence: "
                f"{result.confidence}/100"
            )

            print()

            print("Evidence:")

            for evidence in result.evidence:
                print(f"✓ {evidence}")

            print()

            print(
                "Conclusion:"
            )

            print(
                result.conclusion
            )

            print()

    print("=" * 68)

    if results:

        print(
            "V5.4.1 MODULE TEST: PASS"
        )

        print(
            "CROSS-EQUIPMENT CORRELATION: PASS"
        )

    else:

        print(
            "V5.4.1 MODULE TEST: ATTENTION"
        )

    print("=" * 68)


if __name__ == "__main__":
    run_test()
