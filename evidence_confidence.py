from datetime import datetime


def calculate_confidence(
    evidence_count,
    relationship_count,
    verification_count,
    contradiction_count=0
):
    """
    Calculate an explainable confidence level.

    This is an evidence-strength score, NOT a probability.
    """

    score = 0

    score += min(evidence_count * 15, 45)
    score += min(relationship_count * 10, 30)
    score += min(verification_count * 5, 15)

    score -= min(contradiction_count * 10, 30)

    score = max(0, min(score, 100))

    if score >= 75:
        level = "HIGH"
    elif score >= 50:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "score": score,
        "level": level
    }


def build_evidence_confidence(
    equipment_tag,
    conclusion,
    facts=None,
    relationships=None,
    possible_causes=None,
    verification_checks=None,
    contradictions=None
):
    """
    Build an explainable evidence and confidence report.
    """

    facts = facts or []
    relationships = relationships or []
    possible_causes = possible_causes or []
    verification_checks = verification_checks or []
    contradictions = contradictions or []

    confidence = calculate_confidence(
        len(facts),
        len(relationships),
        len(verification_checks),
        len(contradictions)
    )

    if verification_checks:
        verification_status = (
            "FIELD VERIFICATION REQUIRED"
        )
    else:
        verification_status = (
            "NO ADDITIONAL VERIFICATION IDENTIFIED"
        )

    if contradictions:
        evidence_quality = "MIXED"
    elif len(facts) >= 3 and len(relationships) >= 2:
        evidence_quality = "STRONG"
    elif facts:
        evidence_quality = "LIMITED"
    else:
        evidence_quality = "INSUFFICIENT"

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "equipment": equipment_tag,
        "conclusion": conclusion,
        "evidence_quality": evidence_quality,
        "confidence": confidence,
        "supporting_facts": facts,
        "relationships": relationships,
        "possible_causes": possible_causes,
        "verification_required": verification_status,
        "verification_checks": verification_checks,
        "contradictions": contradictions,
        "explainability": {
            "why": facts,
            "relationship_basis": relationships,
            "possible_explanation": possible_causes,
            "what_is_unknown": (
                "Actual field condition has not "
                "yet been physically verified."
            )
        }
    }
