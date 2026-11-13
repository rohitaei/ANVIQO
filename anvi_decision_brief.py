"""Evidence-first equipment decision briefs for ANVIQO."""
from __future__ import annotations
import re
from typing import Any, Dict

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def _norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def build_equipment_brief(snapshot: Dict[str, Any], requested_tag: str) -> Dict[str, Any]:
    """Summarize one exact equipment observation; never fuzzy-match or invent data."""
    tag = str(requested_tag or "").strip()
    if not tag:
        raise ValueError("An exact equipment tag is required.")
    points = snapshot.get("points") if isinstance(snapshot, dict) else None
    if not isinstance(points, list):
        points = snapshot.get("records") if isinstance(snapshot, dict) else None
    if not isinstance(points, list):
        raise ValueError("Observation points are unavailable.")

    matches = [
        point for point in points
        if isinstance(point, dict) and _norm(point.get("tag")) == _norm(tag)
    ]
    if len(matches) != 1:
        return {
            "status": "EQUIPMENT_NOT_FOUND" if not matches else "AMBIGUOUS_EQUIPMENT_IDENTITY",
            "requested_tag": tag,
            "match_count": len(matches),
            "scope": "EXACT_SELECTED_PLANT_EVIDENCE",
            **SAFETY,
        }

    point = matches[0]
    state = str(point.get("state") or point.get("status") or "UNKNOWN").upper()
    priority = {
        "CRITICAL": ("P1_HUMAN_REVIEW", "Prompt human review"),
        "WARNING": ("P2_ENGINEERING_REVIEW", "Engineering review recommended"),
        "HEALTHY": ("ROUTINE_MONITORING", "Continue routine monitoring"),
    }.get(state, ("EVIDENCE_REVIEW", "Validate the observation before drawing a conclusion"))
    next_step = {
        "CRITICAL": (
            "Check the indication against an independent measurement and the approved "
            "operating envelope; inspect related process conditions under site procedures."
        ),
        "WARNING": (
            "Review recent trend, instrument condition and process operating limits; "
            "confirm the signal before deciding on maintenance."
        ),
        "HEALTHY": (
            "No abnormal state is indicated by this observation; continue normal "
            "monitoring and compare with the next observation window."
        ),
    }.get(state, "Confirm tag identity and obtain a valid observation before action.")

    evidence = {
        key: point.get(key) for key in (
            "tag", "name", "description", "area", "service", "io_type",
            "plc_address", "panel", "value", "state", "status",
            "changed", "event_active", "timestamp", "mode", "source",
            "metadata",
        )
    }
    mode = str(snapshot.get("mode") or point.get("mode") or "UNKNOWN").upper()
    return {
        "status": "BRIEF_READY",
        "requested_tag": tag,
        "equipment": evidence,
        "decision_priority": priority[0],
        "what_matters": priority[1],
        "recommended_human_review": next_step,
        "evidence_quality": (
            "SIMULATION_ONLY_NOT_LIVE_TELEMETRY" if mode == "SIMULATION"
            else "ONBOARDING_DATA_NOT_LIVE_TELEMETRY" if mode in ("ONBOARDING", "ONBOARDING_DATA")
            else "SOURCE_REQUIRES_SITE_VALIDATION"
        ),
        "evidence_scope": "ONE_EXACT_SELECTED_PLANT_OBSERVATION",
        "limitations": [
            "A state label is not a confirmed physical fault diagnosis.",
            "No root cause, failure probability, or remaining useful life is inferred.",
            "Values and units are shown exactly as supplied by the source.",
            "A qualified person must verify evidence and follow site procedures.",
        ],
        **SAFETY,
    }
