"""
ANVIQO Phase 5 — Human & Management Intelligence V1

A separate decision-support layer over certified V5 and Phase 4 intelligence.
It does not replace existing reasoning engines and never executes actions.
"""

from datetime import datetime

VERSION = "PHASE5-V1"

SAFETY_BOUNDARY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
    "causation_claim": False,
}


def _items(value):
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    return []


def build_management_brief(executive=None, phase4=None, shift=None):
    """Create an evidence-backed HOD/management brief; no new plant reasoning."""
    executive = executive if isinstance(executive, dict) else {}
    phase4 = phase4 if isinstance(phase4, dict) else {}
    shift = shift if isinstance(shift, dict) else {}

    risks = _items(executive.get("top_equipment_risks"))
    decisions = _items(executive.get("decision_queue"))
    changes = executive.get("what_changed", [])
    if not isinstance(changes, list):
        changes = []

    priorities = []
    for item in risks:
        priorities.append({
            "equipment": item.get("equipment", "UNKNOWN"),
            "priority": item.get("priority", 0),
            "status": item.get("status", "UNKNOWN"),
            "reason": item.get("reason", ""),
            "human_action": "REVIEW",
        })
    for item in decisions:
        if not any(x["equipment"] == item.get("equipment", "UNKNOWN") for x in priorities):
            priorities.append({
                "equipment": item.get("equipment", "UNKNOWN"),
                "priority": item.get("priority", 0),
                "status": item.get("decision", "REVIEW REQUIRED"),
                "reason": item.get("recommendation", ""),
                "human_action": "REVIEW",
            })

    priorities.sort(key=lambda x: float(x.get("priority", 0) or 0), reverse=True)

    evidence_available = bool(
        priorities or changes or phase4.get("domains") or shift
    )

    if not evidence_available:
        management_state = "INSUFFICIENT_EVIDENCE"
        message = "Insufficient verified evidence for a management brief."
    elif priorities:
        management_state = "REVIEW_REQUIRED"
        message = (
            f"Management review required for {priorities[0]['equipment']} "
            f"(priority {priorities[0]['priority']}/100)."
        )
    else:
        management_state = "MONITOR"
        message = "Evidence is available; no prioritized management action was supplied."

    return {
        "version": VERSION,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "management_state": management_state,
        "management_message": message,
        "plant_situation": executive.get("plant_situation", "NO DATA"),
        "plant_health": executive.get("plant_health", {"status": "NO DATA", "score": None}),
        "top_priorities": priorities[:10],
        "what_changed": changes[:10],
        "shift_summary": shift,
        "phase4_evidence_present": bool(phase4.get("domains")),
        "evidence_available": evidence_available,
        "safety_boundary": dict(SAFETY_BOUNDARY),
    }


def create_human_action_queue(brief, actions=None):
    """Normalize human follow-up items without authorizing or executing them."""
    brief = brief if isinstance(brief, dict) else {}
    supplied = actions if isinstance(actions, list) else []
    queue = []

    for item in supplied:
        if not isinstance(item, dict):
            continue
        queue.append({
            "action_id": item.get("action_id", "UNASSIGNED"),
            "owner": item.get("owner", "UNASSIGNED"),
            "equipment": item.get("equipment", "PLANT"),
            "action": item.get("action", "REVIEW REQUIRED"),
            "status": item.get("status", "OPEN"),
            "priority": item.get("priority", 0),
            "approval_required": True,
            "approved": False,
            "executed": False,
        })

    if not queue and brief.get("top_priorities"):
        for index, item in enumerate(brief["top_priorities"], 1):
            queue.append({
                "action_id": f"REVIEW-{index}",
                "owner": "UNASSIGNED",
                "equipment": item.get("equipment", "UNKNOWN"),
                "action": item.get("human_action", "REVIEW"),
                "status": "OPEN",
                "priority": item.get("priority", 0),
                "approval_required": True,
                "approved": False,
                "executed": False,
            })

    return {
        "version": VERSION,
        "action_queue": queue[:20],
        "safety_boundary": dict(SAFETY_BOUNDARY),
    }


def record_human_decision(action, decision, reviewer=None, note=""):
    """Record a human decision; this function does not execute the action."""
    action = action if isinstance(action, dict) else {}
    decision = str(decision or "").upper()
    allowed = {"APPROVE", "REJECT", "DEFER", "ACKNOWLEDGE"}
    if decision not in allowed:
        return {"status": "ERROR", "message": "Unsupported human decision."}

    result = dict(action)
    result.update({
        "decision": decision,
        "reviewer": reviewer or "UNASSIGNED",
        "decision_note": note,
        "approved": decision == "APPROVE",
        "executed": False,
        "decision_recorded": True,
        "human_decision_required": True,
    })
    return result
