import json
import os
from collections import Counter


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


def load_learning_evidence():
    if not os.path.exists(DB_FILE):
        return []

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def calculate_evidence_strength(
    verified_actions
):
    """
    Determine evidence strength from the
    number of unique verified outcomes.

    0-1  : INSUFFICIENT DATA
    2-4  : DEVELOPING
    5+   : STRONG
    """

    if verified_actions < 2:
        return "INSUFFICIENT DATA"

    if verified_actions < 5:
        return "DEVELOPING"

    return "STRONG"


def aggregate_learning_evidence(
    equipment=None
):
    records = load_learning_evidence()

    if equipment is not None:

        records = [
            record
            for record in records
            if record.get(
                "equipment"
            ) == equipment
        ]

    valid_records = []

    for record in records:

        if not record.get(
            "learning_eligible",
            False
        ):
            continue

        outcome = record.get(
            "outcome"
        )

        if outcome not in VALID_OUTCOMES:
            continue

        valid_records.append(
            record
        )

    counts = Counter(
        record["outcome"]
        for record in valid_records
    )

    verified_actions = len(
        valid_records
    )

    improved = counts.get(
        "IMPROVED",
        0
    )

    unchanged = counts.get(
        "UNCHANGED",
        0
    )

    worsened = counts.get(
        "WORSENED",
        0
    )

    unknown = counts.get(
        "UNKNOWN",
        0
    )

    if verified_actions > 0:
        improvement_rate = (
            improved
            / verified_actions
        )
    else:
        improvement_rate = 0.0

    evidence_strength = (
        calculate_evidence_strength(
            verified_actions
        )
    )

    return {
        "equipment":
            equipment,
        "verified_actions":
            verified_actions,
        "improved":
            improved,
        "unchanged":
            unchanged,
        "worsened":
            worsened,
        "unknown":
            unknown,
        "improvement_rate":
            improvement_rate,
        "evidence_strength":
            evidence_strength
    }


def aggregate_all_equipment():
    records = load_learning_evidence()

    equipment_list = sorted(
        {
            record.get(
                "equipment"
            )
            for record in records
            if record.get(
                "equipment"
            )
        }
    )

    results = []

    for equipment in equipment_list:

        results.append(
            aggregate_learning_evidence(
                equipment
            )
        )

    return {
        "equipment_count":
            len(results),
        "results":
            results
    }
