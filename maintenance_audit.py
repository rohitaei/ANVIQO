import json
import os
from datetime import datetime


DB_FILE = os.path.join(
    "database",
    "maintenance_recommendation_audit.json"
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

        if not isinstance(
            data,
            list
        ):
            return []

        return data

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


def record_recommendation_decision(
    equipment,
    current_evidence,
    historical_pattern,
    context_status,
    verified_actions,
    required_actions,
    evidence_status,
    recommendation_status,
    reason
):
    """
    Record an Anvi maintenance recommendation
    decision for auditability.
    """

    records = load_audit()

    record = {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment,
        "current_evidence":
            current_evidence or [],
        "historical_pattern":
            historical_pattern,
        "context_status":
            context_status,
        "verified_actions":
            verified_actions,
        "required_actions":
            required_actions,
        "evidence_status":
            evidence_status,
        "recommendation_status":
            recommendation_status,
        "reason":
            reason,
        "human_verification_required":
            True
    }

    records.append(
        record
    )

    save_audit(
        records
    )

    return {
        "success": True,
        "audit_record": record
    }


def get_recommendation_audit(
    equipment=None
):
    """
    Return recommendation audit records.
    """

    records = load_audit()

    if equipment:

        records = [
            record
            for record in records
            if record.get(
                "equipment"
            ) == equipment
        ]

    return {
        "record_count": len(
            records
        ),
        "records": records
    }
