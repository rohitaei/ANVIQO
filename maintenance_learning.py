from maintenance_actions import (
    load_actions
)


VALID_OUTCOMES = {
    "IMPROVED",
    "UNCHANGED",
    "WORSENED",
    "UNKNOWN"
}


def build_maintenance_learning(
    equipment_tag=None
):
    """
    Analyze verified maintenance outcomes.

    Only VERIFIED actions are included.
    """

    data = load_actions()

    if equipment_tag:
        equipment_items = {
            equipment_tag: data.get(
                equipment_tag,
                []
            )
        }
    else:
        equipment_items = data

    total = 0
    improved = 0
    unchanged = 0
    worsened = 0
    unknown = 0

    verified_actions = []

    for equipment, records in (
        equipment_items.items()
    ):

        for record in records:

            if record.get(
                "status"
            ) != "VERIFIED":
                continue

            outcome = str(
                record.get(
                    "outcome",
                    "UNKNOWN"
                )
            ).strip().upper()

            if outcome not in VALID_OUTCOMES:
                outcome = "UNKNOWN"

            total += 1

            if outcome == "IMPROVED":
                improved += 1

            elif outcome == "UNCHANGED":
                unchanged += 1

            elif outcome == "WORSENED":
                worsened += 1

            elif outcome == "UNKNOWN":
                unknown += 1

            verified_actions.append({
                "equipment": equipment,
                "action": record.get(
                    "action"
                ),
                "outcome": outcome,
                "verified_at": record.get(
                    "verified_at"
                ),
                "source_prediction": record.get(
                    "source_prediction"
                )
            })

    if total:

        improvement_rate = round(
            (improved / total) * 100,
            1
        )

    else:
        improvement_rate = 0

    if total >= 5:

        if improvement_rate >= 80:
            learning_status = "STRONG"

        elif improvement_rate >= 60:
            learning_status = "DEVELOPING"

        else:
            learning_status = "WEAK"

    else:
        learning_status = "INSUFFICIENT DATA"

    return {
        "equipment": equipment_tag
        if equipment_tag
        else "ALL EQUIPMENT",
        "verified_actions": total,
        "improved": improved,
        "unchanged": unchanged,
        "worsened": worsened,
        "unknown": unknown,
        "improvement_rate": improvement_rate,
        "learning_status": learning_status,
        "actions": verified_actions
    }


def build_action_effectiveness(
    equipment_tag
):
    """
    Return a simple effectiveness summary
    for one equipment item.
    """

    result = build_maintenance_learning(
        equipment_tag
    )

    if result[
        "verified_actions"
    ] == 0:

        return {
            "equipment": equipment_tag,
            "status": "NO VERIFIED DATA",
            "message": (
                "No verified maintenance outcomes "
                "are available."
            )
        }

    return {
        "equipment": equipment_tag,
        "verified_actions": result[
            "verified_actions"
        ],
        "improved": result[
            "improved"
        ],
        "unchanged": result[
            "unchanged"
        ],
        "worsened": result[
            "worsened"
        ],
        "improvement_rate": result[
            "improvement_rate"
        ],
        "learning_status": result[
            "learning_status"
        ]
    }
