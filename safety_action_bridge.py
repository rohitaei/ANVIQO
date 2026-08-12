import json
import os
import uuid
from datetime import datetime

from maintenance_safety import (
    get_safety_history
)

from safety_audit import (
    record_gate_event
)


DB_FILE = os.path.join(
    "database",
    "safety_action_bridge.json"
)


def ensure_database():
    os.makedirs(
        "database",
        exist_ok=True
    )

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f, indent=4)


def load_actions():
    ensure_database()

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_actions(records):
    ensure_database()

    with open(DB_FILE, "w") as f:
        json.dump(records, f, indent=4)


def authorize_maintenance_action(
    gate_id,
    equipment,
    action,
    technician
):
    """
    Authorize a maintenance action only when
    the referenced safety gate is HUMAN APPROVED.

    This function does NOT execute maintenance.
    It only creates a software authorization record.
    """

    history = get_safety_history(
        equipment=equipment
    )

    matching_gate = None

    for record in history["records"]:

        if record.get(
            "gate_id"
        ) == gate_id:

            matching_gate = record
            break

    if matching_gate is None:

        return {
            "success": False,
            "authorization_status": "REJECTED",
            "message": "Safety gate not found."
        }

    if matching_gate.get(
        "gate_status"
    ) != "HUMAN APPROVED":

        record_gate_event(
            gate_id=gate_id,
            equipment=equipment,
            event="MAINTENANCE_ACTION_REJECTED",
            performed_by=technician,
            details={
                "reason":
                    "Safety gate is not human approved.",
                "action":
                    action
            }
        )

        return {
            "success": False,
            "authorization_status": "REJECTED",
            "message":
                "Maintenance action cannot proceed. "
                "Human approval is required."
        }

    records = load_actions()

    action_id = (
        "ACTION-"
        + datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )
        + "-"
        + uuid.uuid4().hex[:6].upper()
    )

    authorization = {
        "action_id":
            action_id,
        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),
        "gate_id":
            gate_id,
        "equipment":
            equipment,
        "action":
            action,
        "technician":
            technician,
        "authorization_status":
            "AUTHORIZED",
        "execution_status":
            "NOT EXECUTED",
        "outcome":
            None,
        "verification":
            None
    }

    records.append(
        authorization
    )

    save_actions(
        records
    )

    record_gate_event(
        gate_id=gate_id,
        equipment=equipment,
        event="MAINTENANCE_ACTION_AUTHORIZED",
        performed_by=technician,
        details={
            "action_id":
                action_id,
            "action":
                action,
            "execution_status":
                "NOT EXECUTED"
        }
    )

    return {
        "success": True,
        "authorization_status":
            "AUTHORIZED",
        "authorization":
            authorization
    }


def get_action_authorization(
    action_id
):
    records = load_actions()

    for record in records:

        if record.get(
            "action_id"
        ) == action_id:

            return {
                "success": True,
                "authorization":
                    record
            }

    return {
        "success": False,
        "message":
            "Action authorization not found."
    }
