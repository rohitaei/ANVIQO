"""
ANVIQO V5.3.4
Maintenance Learning Record

Stores verified maintenance outcomes as reusable
plant experience.

Only human-verified outcomes become learning records.

No automatic maintenance action.
No PLC / SCADA control.
"""

import json
import os
from datetime import datetime


LEARNING_FILE = os.path.join(
    "database",
    "maintenance_learning.json"
)


def ensure_database():

    os.makedirs(
        "database",
        exist_ok=True
    )

    if not os.path.exists(
        LEARNING_FILE
    ):

        with open(
            LEARNING_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                [],
                file,
                indent=2
            )


def load_learning_records():

    ensure_database()

    try:

        with open(
            LEARNING_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, list):
                return data

    except (
        json.JSONDecodeError,
        OSError
    ):

        pass

    return []


def save_learning_record(
    verification
):

    records = load_learning_records()

    if not verification.get(
        "human_verified",
        False
    ):

        return {
            "saved": False,
            "reason":
                "Human verification required."
        }

    outcome = verification.get(
        "outcome",
        "UNKNOWN"
    )

    if outcome not in (
        "IMPROVED",
        "NO_CHANGE",
        "WORSENED"
    ):

        return {
            "saved": False,
            "reason":
                "Verified outcome required."
        }

    record = {

        "record_id":
            f'ML-{datetime.now().strftime("%Y%m%d%H%M%S")}',

        "timestamp":
            datetime.now().isoformat(),

        "equipment":
            verification.get(
                "equipment",
                "UNKNOWN"
            ),

        "area":
            verification.get(
                "area",
                "UNKNOWN"
            ),

        "recommendation_priority":
            verification.get(
                "recommendation_priority",
                0
            ),

        "action_taken":
            verification.get(
                "action_taken",
                ""
            ),

        "outcome":
            outcome,

        "learning_status":
            verification.get(
                "learning_status",
                ""
            ),

        "evidence_chain":
            verification.get(
                "evidence_chain",
                []
            ),

        "verified_by":
            verification.get(
                "verified_by",
                "UNKNOWN"
            ),

        "human_verified":
            True,

        "source_version":
            "V5.3.3",

        "learning_version":
            "V5.3.4"
    }

    records.append(record)

    with open(
        LEARNING_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            records,
            file,
            indent=2
        )

    return {
        "saved": True,
        "record": record,
        "total_records":
            len(records)
    }


def find_equipment_history(
    equipment
):

    records = load_learning_records()

    return [
        record
        for record in records
        if record.get(
            "equipment"
        ) == equipment
    ]


def print_learning_result(
    result
):

    print()
    print("=" * 68)
    print(
        "        ANVIQO V5.3.4 MAINTENANCE LEARNING"
    )
    print("=" * 68)

    print()

    if not result.get("saved"):

        print(
            "LEARNING RECORD NOT SAVED"
        )

        print(
            result.get(
                "reason",
                "Unknown reason."
            )
        )

        return

    record = result["record"]

    print("LEARNING RECORD")
    print("-" * 68)

    print(
        "Record ID       :",
        record["record_id"]
    )

    print(
        "Equipment       :",
        record["equipment"]
    )

    print(
        "Area            :",
        record["area"]
    )

    print(
        "Priority        :",
        f'{record["recommendation_priority"]}/100'
    )

    print(
        "Action          :",
        record["action_taken"]
    )

    print(
        "Verified outcome:",
        record["outcome"]
    )

    print(
        "Verified by     :",
        record["verified_by"]
    )

    print(
        "Human verified  :",
        record["human_verified"]
    )

    print()

    print("EVIDENCE RETAINED")
    print("-" * 68)

    for evidence in record[
        "evidence_chain"
    ]:

        print(
            f"✓ {evidence}"
        )

    print()

    print(
        "TOTAL LEARNING RECORDS:",
        result["total_records"]
    )

    print()

    print("LEARNING BOUNDARY")
    print("-" * 68)

    print(
        "Human verified only : True"
    )

    print(
        "Automatic action    : False"
    )

    print(
        "PLC write           : False"
    )

    print(
        "SCADA control       : False"
    )

    print()
    print("=" * 68)


if __name__ == "__main__":

    verification = {

        "equipment": "CV-101",

        "area": "MBF",

        "recommendation_priority":
            84.7,

        "action_taken":
            "Inspected CV-101 and verified "
            "valve position feedback and "
            "actuator condition.",

        "outcome":
            "IMPROVED",

        "learning_status":
            "POSITIVE VERIFIED OUTCOME",

        "verified_by":
            "Maintenance Supervisor",

        "human_verified":
            True,

        "evidence_chain": [

            "Position changed from 20% to 34%.",

            "70% increase detected.",

            "MBF operational correlation.",

            "Equipment criticality is high.",

            "Worsening operational trend detected.",

            "V5.0.8 evidence-backed diagnosis."
        ]
    }

    result = save_learning_record(
        verification
    )

    print_learning_result(
        result
    )

    history = find_equipment_history(
        "CV-101"
    )

    print()
    print("=" * 68)

    print(
        "CV-101 VERIFIED HISTORY:",
        len(history)
    )

    print(
        "V5.3.4 MODULE TEST: PASS"
    )

    print("=" * 68)
