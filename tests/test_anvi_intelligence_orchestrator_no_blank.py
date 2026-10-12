from anvi_intelligence_orchestrator import investigate


def test_missing_evidence_returns_explanation_not_blank_answer():
    result = investigate(
        "Tell me about PT-303",
        "plant-test-only",
        "Test Plant",
        lambda _question: {
            "answer": "",
            "evidence_status": "INSUFFICIENT_EVIDENCE",
            "evidence": [],
        },
    )
    assert result["answer"].strip()
    assert "cross-plant fallback" in result["answer"].lower()
    assert result["evidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert result["read_only"] is True
    assert result["plc_write"] is False
    assert result["scada_control"] is False
    assert result["automatic_authorization"] is False
    assert result["automatic_execution"] is False
    assert result["human_decision_required"] is True
