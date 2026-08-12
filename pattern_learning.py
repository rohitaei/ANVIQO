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


def aggregate_pattern(
    pattern
):
    records = load_learning_evidence()

    matched = []

    for record in records:

        if not record.get(
            "learning_eligible",
            False
        ):
            continue

        if record.get(
            "pattern"
        ) != pattern:
            continue

        if record.get(
            "outcome"
        ) not in VALID_OUTCOMES:
            continue

        matched.append(record)

    counts = Counter(
        record["outcome"]
        for record in matched
    )

    verified_actions = len(
        matched
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

    if verified_actions < 2:
        evidence_status = (
            "INSUFFICIENT DATA"
        )
    elif verified_actions < 5:
        evidence_status = (
            "DEVELOPING"
        )
    else:
        evidence_status = "STRONG"

    equipment = sorted(
        {
            record.get(
                "equipment"
            )
            for record in matched
            if record.get(
                "equipment"
            )
        }
    )

    return {
        "pattern":
            pattern,
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
        "equipment":
            equipment,
        "improvement_rate":
            improvement_rate,
        "evidence_status":
            evidence_status
    }


def aggregate_all_patterns():
    records = load_learning_evidence()

    patterns = sorted(
        {
            record.get(
                "pattern"
            )
            for record in records
            if record.get(
                "pattern"
            )
        }
    )

    results = []

    for pattern in patterns:

        results.append(
            aggregate_pattern(
                pattern
            )
        )

    return {
        "pattern_count":
            len(results),
        "patterns":
            results
    }
