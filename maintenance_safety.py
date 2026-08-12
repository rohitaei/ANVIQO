import json
import os
import uuid
from datetime import datetime

from safety_audit import record_gate_event


DB_FILE = os.path.join(
    "database",
    "maintenance_safety.json"
)


def ensure_database():
    os.makedirs("database", exist_ok=True)

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f, indent=4)


def load_safety_records():
    ensure_database()

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_safety_records(records):
    ensure_database()

    with open(DB_FILE, "w") as f:
        json.dump(records, f, indent=4)


def create_safety_gate(
    equipment,
    recommendation_status,
    evidence_status,
    context_status,
    reason
):
    records = load_safety_records()

    gate_id = (
        "GATE-"
        + datetime.now().strftime("%Y%m%d-%H%M%S")
        + "-"
        + uuid.uuid4().hex[:6].upper()
    )

    if recommendation_status != "RECOMMENDED":
        gate_status = "BLOCKED"

        decision = (
            "Recommendation cannot proceed "
            "because the evidence threshold "
            "has not been satisfied."
        )

    else:
        gate_status = "AWAITING HUMAN APPROVAL"

        decision = (
            "Evidence threshold satisfied, but "
            "human approval is still required."
        )

    record = {
        "gate_id": gate_id,
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment,
        "recommendation_status": recommendation_status,
        "evidence_status": evidence_status,
        "context_status": context_status,
        "gate_status": gate_status,
        "human_approval_required": True,
        "human_approved": False,
        "decision": decision,
        "reason": reason,
        "approved_by": None,
        "approved_at": None
    }

    records.append(record)
    save_safety_records(records)

    record_gate_event(
        gate_id=gate_id,
        equipment=equipment,
        event="GATE_CREATED",
        performed_by="ANVI",
        details={
            "recommendation_status": recommendation_status,
            "evidence_status": evidence_status,
            "context_status": context_status,
            "gate_status": gate_status
        }
    )

    if gate_status == "BLOCKED":

        record_gate_event(
            gate_id=gate_id,
            equipment=equipment,
            event="RECOMMENDATION_BLOCKED",
            performed_by="ANVI",
            details={
                "reason": reason,
                "evidence_status": evidence_status
            }
        )

    else:

        record_gate_event(
            gate_id=gate_id,
            equipment=equipment,
            event="AWAITING_HUMAN_APPROVAL",
            performed_by="ANVI",
            details={
                "human_approval_required": True
            }
        )

    return {
        "success": True,
        "safety_gate": record
    }


def approve_safety_gate(
    gate_id,
    approved_by
):
    if not approved_by:
        return {
            "success": False,
            "message": "Human approver identity is required."
        }

    records = load_safety_records()

    for record in records:

        if record.get("gate_id") != gate_id:
            continue

        equipment = record.get("equipment")

        if record.get("gate_status") == "BLOCKED":

            record_gate_event(
                gate_id=gate_id,
                equipment=equipment,
                event="APPROVAL_REJECTED_BLOCKED_GATE",
                performed_by=approved_by,
                details={
                    "reason": "Safety gate is blocked."
                }
            )

            return {
                "success": False,
                "message": (
                    "Safety gate is blocked. "
                    "Insufficient evidence."
                )
            }

        if record.get("human_approved"):

            record_gate_event(
                gate_id=gate_id,
                equipment=equipment,
                event="APPROVAL_REJECTED_ALREADY_APPROVED",
                performed_by=approved_by,
                details={
                    "approved_by": record.get("approved_by")
                }
            )

            return {
                "success": False,
                "message": "Safety gate has already been approved."
            }

        record["human_approved"] = True
        record["gate_status"] = "HUMAN APPROVED"
        record["approved_by"] = approved_by
        record["approved_at"] = datetime.now().isoformat(
            timespec="seconds"
        )

        save_safety_records(records)

        record_gate_event(
            gate_id=gate_id,
            equipment=equipment,
            event="HUMAN_APPROVED",
            performed_by=approved_by,
            details={
                "approved_at": record["approved_at"]
            }
        )

        record_gate_event(
            gate_id=gate_id,
            equipment=equipment,
            event="APPROVAL_RECORDED",
            performed_by=approved_by,
            details={
                "approval_status": "HUMAN APPROVED"
            }
        )

        return {
            "success": True,
            "safety_gate": record
        }

    return {
        "success": False,
        "message": "Safety gate not found."
    }


def get_safety_history(equipment=None):
    records = load_safety_records()

    if equipment:
        records = [
            record
            for record in records
            if record.get("equipment") == equipment
        ]

    return {
        "record_count": len(records),
        "records": records
    }
