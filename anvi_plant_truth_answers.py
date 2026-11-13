"""Evidence-backed answers for plant health, alarms and change questions."""
from __future__ import annotations
import re
from typing import Any, Dict


SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
}


def recognizes_plant_truth_question(question: str) -> bool:
    q = str(question or "").lower()
    return bool(
        re.search(r"\bplant\s+health\b|\bhow\s+healthy\s+is\s+the\s+plant\b", q)
        or re.search(r"\b(active\s+alarms?|show\s+alarms?)\b", q)
        or re.search(r"\bcritical\s+equipment\b", q)
        or re.search(r"\bwhat\s+(?:has\s+)?changed\b|\brecent\s+changes?\b", q)
    )


def _point_line(point: Dict[str, Any]) -> str:
    tag = str(point.get("tag") or point.get("name") or "UNIDENTIFIED")
    desc = str(point.get("description") or point.get("name") or "").strip()
    area = str(point.get("area") or "Area not recorded")
    state = str(point.get("state") or point.get("status") or "UNKNOWN").upper()
    value = point.get("value")
    detail = f" — {desc}" if desc and desc != tag else ""
    value_text = f"; value: {value}" if value is not None else ""
    return f"{tag}{detail} | {area} | {state}{value_text}"


def answer_plant_truth(
    question: str,
    snapshot: Dict[str, Any] | None,
    assurance: Dict[str, Any] | None,
) -> Dict[str, Any] | None:
    if not recognizes_plant_truth_question(question):
        return None
    data = snapshot if isinstance(snapshot, dict) else {}
    quality = assurance if isinstance(assurance, dict) else {}
    points = data.get("points") or data.get("records") or []
    points = [p for p in points if isinstance(p, dict)]
    q = str(question or "").lower()
    mode = str(data.get("mode") or "UNKNOWN").upper()
    source = str(data.get("source") or "UNSPECIFIED")
    findings = quality.get("findings") or []
    checks = quality.get("checks") or {}
    data_note = (
        "SIMULATION ONLY — not live PLC telemetry."
        if mode == "SIMULATION"
        else "ONBOARDING DATA — not live PLC telemetry."
        if mode in ("ONBOARDING", "ONBOARDING_DATA")
        else "Source mode requires site validation."
    )

    if not points:
        answer = (
            "No point-level observation evidence is available for the selected plant. "
            "ANVI did not substitute another plant or a global demo stream."
        )
        return {
            "answer": answer, "domain": "plant_truth",
            "evidence_status": "NO_POINT_EVIDENCE",
            "source": source, "mode": mode,
            "findings": findings, **SAFETY,
        }

    counts = quality.get("state_counts") or {
        "HEALTHY": sum(1 for p in points if str(p.get("state") or p.get("status") or "").upper() == "HEALTHY"),
        "WARNING": sum(1 for p in points if str(p.get("state") or p.get("status") or "").upper() == "WARNING"),
        "CRITICAL": sum(1 for p in points if str(p.get("state") or p.get("status") or "").upper() == "CRITICAL"),
    }
    assurance_status = quality.get("assurance_status") or "ASSURANCE_NOT_AVAILABLE"
    if "plant health" in q or "how healthy is the plant" in q:
        score = quality.get("recomputed_health_score")
        can_report = (
            score is not None
            and checks.get("point_total_reconciled") is True
            and checks.get("state_counts_reconciled") is True
            and checks.get("health_score_reconciled") is True
            and checks.get("timestamp_valid") is True
            and checks.get("snapshot_fresh") is True
        )
        if can_report:
            label = "Simulated plant health index" if mode == "SIMULATION" else "Onboarding-data condition index" if mode in ("ONBOARDING", "ONBOARDING_DATA") else "Evidence-derived condition index"
            answer = (
                f"{label}: {score}/100. "
                f"Points: {len(points)}; healthy: {counts.get('HEALTHY', 0)}; "
                f"warning: {counts.get('WARNING', 0)}; critical: {counts.get('CRITICAL', 0)}. "
                f"Evidence status: {assurance_status}. Source: {source}. {data_note}"
            )
        else:
            answer = (
                "ANVI cannot provide one definitive plant-health score because the selected-plant "
                "evidence is incomplete, stale or internally inconsistent. "
                f"Observed points: {len(points)}; healthy: {counts.get('HEALTHY', 0)}; "
                f"warning: {counts.get('WARNING', 0)}; critical: {counts.get('CRITICAL', 0)}. "
                f"Findings: {', '.join(findings) if findings else 'assurance checks incomplete'}. "
                f"Source: {source}. {data_note}"
            )
        return {
            "answer": answer, "domain": "plant_truth",
            "evidence_status": assurance_status,
            "plant_health_score": score if can_report else None,
            "counts": counts, "source": source, "mode": mode,
            "findings": findings, **SAFETY,
        }

    if "critical equipment" in q:
        selected = [
            p for p in points
            if str(p.get("state") or p.get("status") or "").upper() == "CRITICAL"
        ]
        heading = "Critical equipment"
        counter = f"{len(selected)} critical point(s)"
    elif re.search(r"\b(active\s+alarms?|show\s+alarms?)\b", q):
        selected = [p for p in points if bool(p.get("event_active"))]
        heading = "Active alarms/events"
        counter = f"{len(selected)} active event point(s)"
    else:
        selected = [p for p in points if bool(p.get("changed"))]
        heading = "What Changed — current observation"
        counter = f"{len(selected)} point(s) flagged changed"

    lines = [f"{heading}: {counter}. Selected plant: {data.get('plant_id') or 'authenticated context'}. Source: {source}. {data_note}"]
    if selected:
        lines.extend(_point_line(p) for p in selected[:25])
        if len(selected) > 25:
            lines.append(f"Showing 25 of {len(selected)} matching points.")
    else:
        lines.append("No matching point flags are present in this observation.")
    if findings:
        lines.append("Evidence assurance findings: " + ", ".join(findings))
    return {
        "answer": "\n".join(lines),
        "domain": "plant_truth",
        "evidence_status": assurance_status,
        "matched_count": len(selected),
        "source": source, "mode": mode,
        "findings": findings, **SAFETY,
    }
