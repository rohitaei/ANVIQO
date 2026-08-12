import json
import os
from datetime import datetime

from safety_action_bridge import (
    get_action_authorization
)


DB_FILE = os.path.join(
    "database",
    "action_verification.json"
)


VALID_OUTCOMES = {
    "IMPROVED",
    "UNCHANGED",
    "WORSENED",
    "UNKNOWN"
}


def ensure_database():
    os.makedirs(
        "database",
        exist_ok=True
    )

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f, indent=4)


def load_verifications():
    ensure_database()

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_verifications(records):
    ensure_database()

    with open(DB_FILE, "w") as f:
        json.dump(records, f, indent=4)


def verify_action_outcome(
    action_id,
    outcome,
    verified_by,
    verification_notes=""
):
    """
    Record a human-verified maintenance outcome.

    This function does not execute maintenance.
    It only records the verified result.
    """

    if not verified_by:
        return {
            "success": False,
            "message":
                "Human verifier identity is required."
        }

    outcome = outcome.upper().strip()

    if outcome not in VALID_OUTCOMES:
        return {
            "success": False,
            "message":
                "Invalid outcome. Use "
                "IMPROVED, UNCHANGED, "
                "WORSENED or UNKNOWN."
        }

    authorization = get_action_authorization(
        action_id
    )

    if not authorization.get(
        "success"
    ):
        return {
            "success": False,
            "message":
                "Action authorization not found."
        }

    action = authorization[
        "authorization"
    ]

    if action.get(
        "authorization_status"
    ) != "AUTHORIZED":

        return {
            "success": False,
            "message":
                "Action was not authorized."
        }

    records = load_verifications()

    for record in records:

        if record.get(
            "action_id"
        ) == action_id:

            return {
                "success": False,
                "message":
                    "Action outcome has already "
                    "been verified."
            }

    verification = {
        "action_id":
            action_id,
        "gate_id":
            action.get("gate_id"),
        "equipment":
            action.get("equipment"),
        "action":
            action.get("action"),
        "technician":
            action.get("technician"),
        "outcome":
            outcome,
        "verified_by":
            verified_by,
        "verification_notes":
            verification_notes,
        "verified_at":
            datetime.now().isoformat(
                timespec="seconds"
            )
    }

    records.append(
        verification
    )

    save_verifications(
        records
    )

    return {
        "success": True,
        "verification":
            verification
    }


def get_action_verification(
    action_id
):
    records = load_verifications()

    for record in records:

        if record.get(
            "action_id"
        ) == action_id:

            return {
                "success": True,
                "verification":
                    record
            }

    return {
        "success": False,
        "message":
            "Action verification not found."
    }
