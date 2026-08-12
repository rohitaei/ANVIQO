"""
ANVIQO V5.1.4
Operational Explanation Engine

Converts V5.1 priority results into clear operational explanations.
Read-only intelligence layer. No PLC/SCADA control.
"""

from typing import Dict, Any


def explain_condition(condition: Dict[str, Any]) -> Dict[str, Any]:
    equipment = condition.get("equipment", "Unknown equipment")
    area = condition.get("area", "Unknown area")
    severity = condition.get("severity", "UNKNOWN")
    score = condition.get("priority_score", 0)

    risk = condition.get("risk", 0)
    criticality = condition.get("criticality", 0)
    trend = condition.get("trend", 0)
    evidence = condition.get("evidence", 0)

    evidence_chain = condition.get("evidence_chain", [])

    factors = []

    if risk >= 60:
        factors.append("elevated operational risk")

    if criticality >= 60:
        factors.append("high equipment criticality")

    if trend >= 60:
        factors.append("significant worsening trend")

    if evidence >= 70:
        factors.append("strong supporting evidence")

    if factors:
        reason = (
            f"{equipment} in {area} is receiving {severity.lower()} "
            f"because of " + ", ".join(factors) + "."
        )
    else:
        reason = (
            f"{equipment} in {area} is receiving attention based "
            f"on the available operational evidence."
        )

    return {
        "equipment": equipment,
        "area": area,
        "severity": severity,
        "priority_score": score,
        "explanation": reason,
        "evidence_chain": evidence_chain,
        "factors": {
            "risk": risk,
            "criticality": criticality,
            "trend": trend,
            "evidence": evidence,
        },
        "read_only": True,
        "scada_control": False,
    }


def build_operational_explanations(priority_results):
    return [
        explain_condition(condition)
        for condition in priority_results
    ]


if __name__ == "__main__":

    sample = {
        "equipment": "CV-101",
        "area": "MBF",
        "severity": "IMMEDIATE ATTENTION",
        "priority_score": 85.4,
        "risk": 82,
        "criticality": 92,
        "trend": 76,
        "evidence": 88,
        "evidence_chain": [
            "Position changed from 20% to 34%",
            "70% increase detected",
            "MBF operational correlation",
        ],
    }

    result = explain_condition(sample)

    print("===== ANVIQO V5.1.4 =====")
    print("OPERATIONAL EXPLANATION")
    print("========================")
    print("Equipment :", result["equipment"])
    print("Area      :", result["area"])
    print("Severity  :", result["severity"])
    print("Priority  :", result["priority_score"])
    print("Reason    :", result["explanation"])
    print("Evidence  :")

    for item in result["evidence_chain"]:
        print(" -", item)

    print("Read-only :", result["read_only"])
    print("SCADA     :", result["scada_control"])
    print("========================")

