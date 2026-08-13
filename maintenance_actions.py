import json
import os
from datetime import datetime


DB_FILE = os.path.join(
    "database",
    "maintenance_actions.json"
)


VALID_STATUSES = {
    "PLANNED",
    "IN_PROGRESS",
    "COMPLETED",
    "VERIFIED"
}


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

        with open(
            DB_FILE,
            "w"
        ) as f:

            json.dump(
                {},
                f,
                indent=4
            )


def load_actions():
    ensure_database()

    try:

        with open(
            DB_FILE,
            "r"
        ) as f:

            data = json.load(f)

        if not isinstance(
            data,
            dict
        ):
            return {}

        return data

    except (
        json.JSONDecodeError,
        OSError
    ):

        return {}


def save_actions(data):
    ensure_database()

    with open(
        DB_FILE,
        "w"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )


def record_maintenance_action(
    equipment_tag,
    action,
    technician=None,
    source_prediction=None,
    notes=None
):
    """
    Record a maintenance action.

    The action starts as PLANNED and requires
    later human verification.
    """

    if not equipment_tag:

        return {
            "success": False,
            "message": (
                "Equipment tag is required."
            )
        }

    if not action:

        return {
            "success": False,
            "message": (
                "Maintenance action is required."
            )
        }

    data = load_actions()

    if equipment_tag not in data:

        data[equipment_tag] = []

    record = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment_tag,
        "action": action,
        "technician": technician,
        "source_prediction": (
            source_prediction
        ),
        "notes": notes,
        "status": "PLANNED",
        "outcome": None,
        "verification": None,
        "verified_at": None
    }

    data[
        equipment_tag
    ].append(
        record
    )

    save_actions(
        data
    )

    return {
        "success": True,
        "action": record
    }


def update_action_status(
    equipment_tag,
    timestamp,
    status
):
    """
    Update the operational status of a
    maintenance action.
    """

    status = str(
        status
    ).strip().upper()

    if status not in VALID_STATUSES:

        return {
            "success": False,
            "message": (
                "Invalid status. Use "
                "PLANNED, IN_PROGRESS, "
                "COMPLETED or VERIFIED."
            )
        }

    data = load_actions()

    records = data.get(
        equipment_tag,
        []
    )

    for record in records:

        if record.get(
            "timestamp"
        ) == timestamp:

            record[
                "status"
            ] = status

            save_actions(
                data
            )

            return {
                "success": True,
                "action": record
            }

    return {
        "success": False,
        "message": "Maintenance action not found."
    }


def verify_maintenance_action(
    equipment_tag,
    timestamp,
    outcome,
    verification,
    notes=None
):
    """
    Human-verify the result of a maintenance action.
    """

    outcome = str(
        outcome
    ).strip().upper()

    if outcome not in VALID_OUTCOMES:

        return {
            "success": False,
            "message": (
                "Outcome must be IMPROVED, "
                "UNCHANGED, WORSENED or UNKNOWN."
            )
        }

    if not verification:

        return {
            "success": False,
            "message": (
                "Human verification details "
                "are required."
            )
        }

    data = load_actions()

    records = data.get(
        equipment_tag,
        []
    )

    for record in records:

        if record.get(
            "timestamp"
        ) == timestamp:

            if record.get(
                "status"
            ) == "VERIFIED":

                return {
                    "success": False,
                    "message": (
                        "Maintenance action has "
                        "already been verified and "
                        "cannot be changed."
                    )
                }

            record[
                "status"
            ] = "VERIFIED"

            record[
                "outcome"
            ] = outcome

            record[
                "verification"
            ] = verification

            record[
                "verified_at"
            ] = datetime.now().isoformat(
                timespec="seconds"
            )

            if notes:
                record[
                    "verification_notes"
                ] = notes

            save_actions(
                data
            )

            return {
                "success": True,
                "action": record
            }

    return {
        "success": False,
        "message": "Maintenance action not found."
    }


def get_maintenance_actions(
    equipment_tag
):
    data = load_actions()

    return {
        "equipment": equipment_tag,
        "action_count": len(
            data.get(
                equipment_tag,
                []
            )
        ),
        "actions": data.get(
            equipment_tag,
            []
        )
    }


def get_verified_actions(
    equipment_tag
):
    data = load_actions()

    records = data.get(
        equipment_tag,
        []
    )

    return [
        record
        for record in records
        if record.get(
            "status"
        ) == "VERIFIED"
    ]
