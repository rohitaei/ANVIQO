import json
import os
from datetime import datetime

from action_verification import (
    get_action_verification
)


DB_FILE = os.path.join(
    "database",
    "learning_evidence.json"
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


def load_learning_evidence():
    ensure_database()

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_learning_evidence(records):
    ensure_database()

    with open(DB_FILE, "w") as f:
        json.dump(records, f, indent=4)


def create_learning_evidence(
    action_id,
    pattern
):
    """
    Convert a human-verified maintenance outcome
    into learning evidence.

    Pattern identity is explicitly supplied so
    Anvi never guesses the maintenance pattern.
    """

    if not pattern:
        return {
            "success": False,
            "message":
                "Maintenance pattern is required."
        }

    pattern = pattern.strip().upper()

    verification = get_action_verification(
        action_id
    )

    if not verification.get(
        "success"
    ):
        return {
            "success": False,
            "message":
                "Verified action outcome not found."
        }

    record = verification[
        "verification"
    ]

    outcome = record.get(
        "outcome"
    )

    if outcome not in VALID_OUTCOMES:
        return {
            "success": False,
            "message":
                "Invalid verified outcome."
        }

    verified_by = record.get(
        "verified_by"
    )

    if not verified_by:
        return {
            "success": False,
            "message":
                "Human verification identity is required."
        }

    records = load_learning_evidence()

    for existing in records:

        if existing.get(
            "action_id"
        ) == action_id:

            return {
                "success": False,
                "message":
                    "Learning evidence already exists."
            }

    evidence_id = (
        "EVIDENCE-"
        + datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )
        + "-"
        + os.urandom(3).hex().upper()
    )

    evidence = {
        "evidence_id":
            evidence_id,

        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "action_id":
            action_id,

        "gate_id":
            record.get("gate_id"),

        "equipment":
            record.get("equipment"),

        "pattern":
            pattern,

        "action":
            record.get("action"),

        "technician":
            record.get("technician"),

        "outcome":
            outcome,

        "verified_by":
            verified_by,

        "verified_at":
            record.get("verified_at"),

        "learning_eligible":
            True
    }

    records.append(
        evidence
    )

    save_learning_evidence(
        records
    )

    return {
        "success": True,
        "learning_evidence":
            evidence
    }


def get_learning_evidence(
    equipment=None,
    pattern=None
):
    records = load_learning_evidence()

    filtered = records

    if equipment is not None:
        filtered = [
            record
            for record in filtered
            if record.get(
                "equipment"
            ) == equipment
        ]

    if pattern is not None:
        pattern = pattern.strip().upper()

        filtered = [
            record
            for record in filtered
            if record.get(
                "pattern"
            ) == pattern
        ]

    return {
        "count":
            len(filtered),
        "records":
            filtered
    }
