"""
ANVIQO V5.1.5
Senior / HOD Operational Summary

Creates a concise management-level summary from V5.1
plant operational intelligence.

Read-only. No PLC / WinCC / SCADA control.
"""

from typing import Dict, Any


def build_hod_summary(status: Dict[str, Any]) -> Dict[str, Any]:

    health = status.get("overall_plant_health", 100)
    situation = status.get(
        "situation_summary",
        "No significant operational condition detected."
    )

    critical_areas = status.get("critical_areas", [])
    critical_equipment = status.get("critical_equipment", [])
    active_risks = status.get("active_risks", [])
    changes = status.get("recent_significant_changes", [])

    ranking = status.get(
        "priority_engine", {}
    ).get("ranking", [])

    top = ranking[0] if ranking else None

    if top:
        top_equipment = top.get("equipment", "Unknown")
        top_area = top.get("area", "Unknown")
        top_score = top.get("priority_score", 0)
        top_severity = top.get("severity", "UNKNOWN")
        top_reason = top.get("reason", "Operational condition detected.")
    else:
        top_equipment = "None"
        top_area = "None"
        top_score = 0
        top_severity = "NORMAL"
        top_reason = "No active priority condition."

    if health >= 80:
        health_status = "HEALTHY"
    elif health >= 60:
        health_status = "STABLE"
    elif health >= 40:
        health_status = "DEGRADED"
    else:
        health_status = "CRITICAL"

    summary = (
        f"Plant health is {health}/100 ({health_status}). "
        f"{situation} "
        f"Primary focus is {top_equipment} in {top_area}, "
        f"with priority {top_score}/100."
    )

    return {
        "version": "V5.1.5",
        "plant_health": health,
        "health_status": health_status,
        "situation": situation,

        "primary_area": (
            critical_areas[0] if critical_areas else top_area
        ),

        "top_equipment": top_equipment,
        "top_priority": top_score,
        "top_severity": top_severity,
        "top_reason": top_reason,

        "critical_areas": critical_areas,
        "critical_equipment": critical_equipment,
        "active_risk_count": len(active_risks),
        "significant_change_count": len(changes),

        "management_summary": summary,

        "operational_focus": (
            f"Review {top_equipment} operating condition "
            f"and associated {top_area} process behaviour."
            if top
            else "Continue normal monitoring."
        ),

        "read_only": True,
        "scada_control": False,
    }


if __name__ == "__main__":

    sample_status = {
        "overall_plant_health": 82,
        "situation_summary": (
            "1 immediate attention condition, "
            "1 early warning condition."
        ),
        "critical_areas": ["MBF"],
        "critical_equipment": ["CV-101"],
        "active_risks": [
            {"equipment": "CV-101"}
        ],
        "recent_significant_changes": ["CV-101"],
        "priority_engine": {
            "ranking": [
                {
                    "equipment": "CV-101",
                    "area": "MBF",
                    "priority_score": 85.4,
                    "severity": "IMMEDIATE ATTENTION",
                    "reason": (
                        "Valve position increased significantly "
                        "with strong supporting evidence."
                    ),
                }
            ]
        },
    }

    result = build_hod_summary(sample_status)

    print("===== ANVIQO V5.1.5 =====")
    print("SENIOR / HOD SUMMARY")
    print("========================")
    print("Plant Health :", result["plant_health"])
    print("Status       :", result["health_status"])
    print("Primary Area :", result["primary_area"])
    print("Top Equipment:", result["top_equipment"])
    print("Priority     :", result["top_priority"])
    print("Severity     :", result["top_severity"])
    print()
    print("Management Summary:")
    print(result["management_summary"])
    print()
    print("Operational Focus:")
    print(result["operational_focus"])
    print()
    print("Read-only    :", result["read_only"])
    print("SCADA        :", result["scada_control"])
    print("========================")
