from evidence_context import get_evidence_context


def build_evidence_reasoning_context(equipment):

    evidence = get_evidence_context(
        equipment
    )

    return {
        "equipment": equipment,
        "evidence": evidence,
        "evidence_available": (
            evidence.get("verified_actions", 0) > 0
        ),
        "evidence_strong": (
            evidence.get("evidence_strength")
            == "STRONG"
        ),
        "verified_actions": evidence.get(
            "verified_actions",
            0
        ),
        "improvement_rate": evidence.get(
            "improvement_rate",
            0.0
        )
    }
