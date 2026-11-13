"""Evidence consistency checks for ANVIQO plant observations."""
from __future__ import annotations
from typing import Any, Dict

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
}


def audit_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise ValueError("Snapshot must be an object")
    points = snapshot.get("points")
    if not isinstance(points, list):
        raise ValueError("Snapshot points must be a list")
    actual = {
        "total_io": len(points),
        "healthy": sum(1 for p in points if str(p.get("state", "")).upper() == "HEALTHY"),
        "warning": sum(1 for p in points if str(p.get("state", "")).upper() == "WARNING"),
        "critical": sum(1 for p in points if str(p.get("state", "")).upper() == "CRITICAL"),
        "changed": sum(1 for p in points if bool(p.get("changed"))),
        "active_events": sum(1 for p in points if bool(p.get("event_active"))),
    }
    mismatches = {
        key: {"declared": snapshot.get(key), "calculated": value}
        for key, value in actual.items() if snapshot.get(key) != value
    }
    area_rows = snapshot.get("areas") or []
    area_total = sum(int(row.get("total") or 0) for row in area_rows if isinstance(row, dict))
    if area_rows and area_total != actual["total_io"]:
        mismatches["area_total"] = {"declared": area_total, "calculated": actual["total_io"]}
    score = ((actual["healthy"] + actual["warning"] * 0.5) / actual["total_io"] * 100) if actual["total_io"] else 0.0
    declared_score = snapshot.get("plant_health_score")
    if declared_score is None or abs(float(declared_score) - score) > 0.011:
        mismatches["plant_health_score"] = {"declared": declared_score, "calculated": round(score, 2)}
    return {
        "status": "CONSISTENT" if not mismatches else "INCONSISTENT",
        "audit": "OBSERVATION_ARITHMETIC_AND_SOURCE_CONSISTENCY",
        "snapshot_id": snapshot.get("snapshot_id"),
        "timestamp": snapshot.get("timestamp"),
        "mode": snapshot.get("mode"),
        "source": snapshot.get("source"),
        "counts": actual,
        "plant_health_score": round(score, 2),
        "mismatches": mismatches,
        "checked": ["point_state_counts", "changed_point_count", "active_event_count", "area_total", "plant_health_score"],
        "limitations": [
            "This audit checks internal consistency, not physical process correctness.",
            "SIMULATION data is not live PLC telemetry.",
            "No root cause or equipment failure probability is inferred.",
        ],
        **SAFETY,
    }
