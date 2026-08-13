import json
import os


DB_FILE = os.path.join(
    "database",
    "learning_evidence.json"
)


def load_learning_evidence():
    if not os.path.exists(DB_FILE):
        return []

    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def match_pattern_context(
    equipment,
    current_pattern
):
    """
    Check whether verified historical learning
    evidence for an equipment matches the
    current maintenance pattern.
    """

    records = load_learning_evidence()

    matched_records = []

    for record in records:

        if record.get(
            "equipment"
        ) != equipment:
            continue

        if record.get(
            "pattern"
        ) != current_pattern:
            continue

        if not record.get(
            "learning_eligible",
            False
        ):
            continue

        matched_records.append(
            record
        )

    if matched_records:

        return {
            "equipment":
                equipment,
            "historical_pattern":
                current_pattern,
            "current_pattern":
                current_pattern,
            "context_status":
                "MATCH",
            "matched":
                True,
            "verified_actions":
                len(matched_records),
            "message":
                "Current equipment and pattern "
                "match verified historical evidence."
        }

    return {
        "equipment":
            equipment,
        "historical_pattern":
            None,
        "current_pattern":
            current_pattern,
        "context_status":
            "NO MATCH",
        "matched":
            False,
        "verified_actions":
            0,
        "message":
            "No verified historical evidence "
            "matches this equipment and pattern."
    }


def get_equipment_patterns(
    equipment
):
    records = load_learning_evidence()

    patterns = sorted(
        {
            record.get(
                "pattern"
            )
            for record in records
            if record.get(
                "equipment"
            ) == equipment
            and record.get(
                "pattern"
            )
            and record.get(
                "learning_eligible",
                False
            )
        }
    )

    return {
        "equipment":
            equipment,
        "pattern_count":
            len(patterns),
        "patterns":
            patterns
    }
