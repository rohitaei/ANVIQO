from learning_aggregation import aggregate_learning_evidence


def get_evidence_context(equipment):

    try:
        result = aggregate_learning_evidence(
            equipment
        )

        verified_actions = result.get(
            "verified_actions",
            0
        )

        evidence_strength = result.get(
            "evidence_strength",
            "INSUFFICIENT DATA"
        )

        improvement_rate = result.get(
            "improvement_rate",
            0.0
        )

        improved = result.get(
            "improved",
            0
        )

        unchanged = result.get(
            "unchanged",
            0
        )

        worsened = result.get(
            "worsened",
            0
        )

        unknown = result.get(
            "unknown",
            0
        )

        if verified_actions == 0:
            status = "NO VERIFIED EVIDENCE"

        elif evidence_strength == "DEVELOPING":
            status = "DEVELOPING EVIDENCE"

        elif evidence_strength == "STRONG":
            status = "STRONG EVIDENCE"

        else:
            status = "INSUFFICIENT EVIDENCE"

        return {
            "equipment": equipment,
            "verified_actions": verified_actions,
            "evidence_strength": evidence_strength,
            "status": status,
            "improved": improved,
            "unchanged": unchanged,
            "worsened": worsened,
            "unknown": unknown,
            "improvement_rate": improvement_rate
        }

    except Exception as e:

        return {
            "equipment": equipment,
            "verified_actions": 0,
            "evidence_strength": "ERROR",
            "status": "EVIDENCE ERROR",
            "improved": 0,
            "unchanged": 0,
            "worsened": 0,
            "unknown": 0,
            "improvement_rate": 0.0,
            "error": str(e)
        }
