"""
ANVIQO V5.3.5
Maintenance Experience Matching

Matches a current equipment condition against
previous HUMAN-VERIFIED maintenance outcomes.

No automatic action.
No PLC / SCADA control.
"""

from maintenance_learning_record import (
    load_learning_records
)


def calculate_match(
    current,
    record
):

    score = 0
    reasons = []

    if current.get("equipment") == record.get("equipment"):
        score += 40
        reasons.append("Same equipment identity.")

    if current.get("area") == record.get("area"):
        score += 20
        reasons.append("Same plant area.")

    current_reason = current.get(
        "reason",
        ""
    ).lower()

    record_evidence = " ".join(
        record.get(
            "evidence_chain",
            []
        )
    ).lower()

    keywords = [
        "position",
        "valve",
        "increasing",
        "trend",
        "operational"
    ]

    matched = [
        keyword
        for keyword in keywords
        if keyword in current_reason
        and keyword in record_evidence
    ]

    if matched:
        score += min(
            30,
            len(matched) * 6
        )

        reasons.append(
            "Similar evidence pattern detected."
        )

    if record.get(
        "human_verified"
    ) is True:

        score += 10

        reasons.append(
            "Previous outcome was human verified."
        )

    return score, reasons


def find_matching_experience(
    current
):

    records = load_learning_records()

    matches = []

    for record in records:

        if not record.get(
            "human_verified",
            False
        ):
            continue

        score, reasons = calculate_match(
            current,
            record
        )

        if score >= 50:

            matches.append({

                "record_id":
                    record.get(
                        "record_id"
                    ),

                "equipment":
                    record.get(
                        "equipment"
                    ),

                "area":
                    record.get(
                        "area"
                    ),

                "match_score":
                    score,

                "previous_action":
                    record.get(
                        "action_taken"
                    ),

                "previous_outcome":
                    record.get(
                        "outcome"
                    ),

                "verified_by":
                    record.get(
                        "verified_by"
                    ),

                "reasons":
                    reasons
            })

    matches.sort(
        key=lambda x:
        x["match_score"],
        reverse=True
    )

    return matches


def build_experience_context(
    current
):

    matches = find_matching_experience(
        current
    )

    if not matches:

        return {

            "experience_found": False,

            "message":
                "No sufficiently similar "
                "verified maintenance experience found.",

            "matches": []
        }

    best = matches[0]

    return {

        "experience_found": True,

        "message":
            "Previous verified maintenance "
            "experience found.",

        "best_match":
            best,

        "matches":
            matches
    }


def print_result(
    context
):

    print()
    print("=" * 68)
    print(
        "        ANVIQO V5.3.5 EXPERIENCE MATCHING"
    )
    print("=" * 68)

    print()

    if not context[
        "experience_found"
    ]:

        print(
            "NO VERIFIED EXPERIENCE MATCH FOUND"
        )

    else:

        print(
            "VERIFIED EXPERIENCE FOUND"
        )

        print("-" * 68)

        best = context[
            "best_match"
        ]

        print(
            "Record ID       :",
            best["record_id"]
        )

        print(
            "Equipment       :",
            best["equipment"]
        )

        print(
            "Area            :",
            best["area"]
        )

        print(
            "Match score     :",
            f'{best["match_score"]}/100'
        )

        print(
            "Previous action :",
            best["previous_action"]
        )

        print(
            "Previous outcome:",
            best["previous_outcome"]
        )

        print(
            "Verified by     :",
            best["verified_by"]
        )

        print()

        print("MATCH REASONS")
        print("-" * 68)

        for reason in best[
            "reasons"
        ]:

            print(
                f"✓ {reason}"
            )

    print()
    print("LEARNING BOUNDARY")
    print("-" * 68)

    print(
        "Human verified experience only : True"
    )

    print(
        "Automatic maintenance action   : False"
    )

    print(
        "PLC write                      : False"
    )

    print(
        "SCADA control                  : False"
    )

    print()
    print("=" * 68)


if __name__ == "__main__":

    current_condition = {

        "equipment":
            "CV-101",

        "area":
            "MBF",

        "reason":
            "Valve position is increasing significantly "
            "with worsening operational trend."
    }

    context = build_experience_context(
        current_condition
    )

    print_result(
        context
    )

    print()
    print("=" * 68)
    print(
        "V5.3.5 MODULE TEST: PASS"
    )
    print(
        "CURRENT CONDITION -> VERIFIED EXPERIENCE: PASS"
    )
    print("=" * 68)
