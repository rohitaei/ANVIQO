import json
import os
import uuid
from datetime import datetime


DB_FILE = os.path.join(
    "database",
    "safety_gate_audit.json"
)


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
                [],
                f,
                indent=4
            )


def load_audit():
    ensure_database()

    try:
        with open(
            DB_FILE,
            "r"
        ) as f:

            data = json.load(f)

        return (
            data
            if isinstance(data, list)
            else []
        )

    except (
        json.JSONDecodeError,
        OSError
    ):
        return []


def save_audit(records):
    ensure_database()

    with open(
        DB_FILE,
        "w"
    ) as f:

        json.dump(
            records,
            f,
            indent=4
        )


def record_gate_event(
    gate_id,
    equipment,
    event,
    performed_by=None,
    details=None
):
    """
    Record one immutable-style audit event
    for a safety gate.
    """

    records = load_audit()

    audit_event = {
        "audit_id":
            "AUDIT-"
            + datetime.now().strftime(
                "%Y%m%d-%H%M%S"
            )
            + "-"
            + uuid.uuid4().hex[:6].upper(),
        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),
        "gate_id":
            gate_id,
        "equipment":
            equipment,
        "event":
            event,
        "performed_by":
            performed_by,
        "details":
            details or {}
    }

    records.append(
        audit_event
    )

    save_audit(
        records
    )

    return {
        "success": True,
        "audit_event":
            audit_event
    }


def get_gate_audit(
    gate_id
):
    records = load_audit()

    matching = [
        record
        for record in records
        if record.get(
            "gate_id"
        ) == gate_id
    ]

    return {
        "gate_id":
            gate_id,
        "event_count":
            len(matching),
        "events":
            matching
    }
