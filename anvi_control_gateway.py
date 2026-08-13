"""
ANVIQO CONTROL GATEWAY
======================

Single safety boundary for future PLC / SCADA control.

ARCHITECTURE:
    Voice/Text
        -> ANVI conversational layer
        -> command intent
        -> safety validation
        -> HUMAN APPROVAL
        -> execution adapter

IMPORTANT:
- This module NEVER writes to a real PLC.
- This module NEVER sends a real SCADA command.
- Default execution mode is SIMULATION.
- Every request is logged.
- Real execution requires a future approved adapter.
"""

import json
import os
import uuid
from datetime import datetime


DB_FILE = os.path.join(
    "database",
    "anvi_control_requests.json"
)

EXECUTION_MODE = "SIMULATION"


def _ensure_db():
    os.makedirs("database", exist_ok=True)

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)


def _load():
    _ensure_db()

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except (OSError, json.JSONDecodeError):
        return []


def _save(records):
    _ensure_db()

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def create_control_request(
    command,
    equipment=None,
    tag=None,
    parameter=None,
    value=None,
    requested_by="UNKNOWN",
    source="TEXT",
):
    """
    Create a pending PLC/SCADA control request.

    NO execution occurs here.
    """

    request_id = (
        "CTRL-"
        + datetime.now().strftime("%Y%m%d-%H%M%S")
        + "-"
        + uuid.uuid4().hex[:6].upper()
    )

    request_record = {
        "request_id": request_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "command": command,
        "equipment": equipment,
        "tag": tag,
        "parameter": parameter,
        "value": value,
        "requested_by": requested_by,
        "source": source,
        "mode": EXECUTION_MODE,
        "approval_status": "PENDING HUMAN APPROVAL",
        "execution_status": "NOT EXECUTED",
        "result": None,
    }

    records = _load()
    records.append(request_record)
    _save(records)

    return {
        "success": True,
        "request": request_record,
        "message": (
            "Control request created. "
            "No PLC or SCADA command has been executed. "
            "Human approval is required."
        ),
    }


def get_control_request(request_id):
    for record in _load():
        if record.get("request_id") == request_id:
            return {
                "success": True,
                "request": record,
            }

    return {
        "success": False,
        "message": "Control request not found.",
    }


def approve_control_request(request_id, approved_by):
    """
    Approves a request but STILL does not execute a real PLC/SCADA write.

    Execution remains simulation-only until a dedicated approved adapter
    is connected.
    """

    if not approved_by:
        return {
            "success": False,
            "message": "Human approver identity is required.",
        }

    records = _load()

    for record in records:

        if record.get("request_id") != request_id:
            continue

        if record.get("approval_status") != "PENDING HUMAN APPROVAL":
            return {
                "success": False,
                "message": "Request is no longer pending approval.",
            }

        record["approval_status"] = "HUMAN APPROVED"
        record["approved_by"] = approved_by
        record["approved_at"] = datetime.now().isoformat(
            timespec="seconds"
        )

        # Safety boundary:
        # approval does NOT imply real execution.
        record["execution_status"] = "SIMULATION ONLY"

        record["result"] = {
            "mode": "SIMULATION",
            "message": (
                "Human approval recorded. "
                "No real PLC/SCADA write was performed."
            ),
        }

        _save(records)

        return {
            "success": True,
            "request": record,
        }

    return {
        "success": False,
        "message": "Control request not found.",
    }


def reject_control_request(request_id, rejected_by, reason=""):
    records = _load()

    for record in records:

        if record.get("request_id") != request_id:
            continue

        record["approval_status"] = "REJECTED"
        record["rejected_by"] = rejected_by
        record["rejected_at"] = datetime.now().isoformat(
            timespec="seconds"
        )
        record["rejection_reason"] = reason
        record["execution_status"] = "NOT EXECUTED"

        _save(records)

        return {
            "success": True,
            "request": record,
        }

    return {
        "success": False,
        "message": "Control request not found.",
    }


def list_control_requests():
    return {
        "mode": EXECUTION_MODE,
        "requests": _load(),
    }


def control_capabilities():
    return {
        "voice": True,
        "text": True,
        "plc_write": True,
        "scada_control": True,
        "execution_mode": EXECUTION_MODE,
        "real_plc_write_enabled": False,
        "real_scada_control_enabled": False,
        "human_approval_required": True,
        "reasoning_engine": "EXISTING ANVI ORCHESTRATOR",
        "safety_boundary": "ANVI CONTROL GATEWAY",
    }
