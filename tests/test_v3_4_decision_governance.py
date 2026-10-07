from datetime import datetime, timezone
import tempfile

import pytest

from anvi_v3_4_decision_governance import DecisionGovernanceStore, SAFETY


def store():
    return DecisionGovernanceStore(tempfile.mktemp(suffix=".db"))


def test_evidence_gated_and_human_decision_required():
    s = store()
    with pytest.raises(ValueError, match="DECISION_EVIDENCE_INSUFFICIENT"):
        s.create(
            organization_id="O1", plant_id="P1", subject_type="EQUIPMENT",
            subject_id="PT-303", recommendation="Review instrument health",
            evidence_ids=[], evidence_status="NO_EVIDENCE",
        )
    row = s.create(
        organization_id="O1", plant_id="P1", subject_type="EQUIPMENT",
        subject_id="PT-303", recommendation="Review instrument health",
        evidence_ids=["obs-1", "event-1"], evidence_status="EVIDENCE_AVAILABLE",
    )
    assert row["decision"] == "PENDING"
    assert row["outcome"] == "UNKNOWN"
    assert row["safety"] == SAFETY


def test_approval_then_outcome_and_persistence():
    path = tempfile.mktemp(suffix=".db")
    s = DecisionGovernanceStore(path)
    row = s.create(
        organization_id="O1", plant_id="P1", subject_type="EQUIPMENT",
        subject_id="PT-303", recommendation="Inspect transmitter",
        evidence_ids=["obs-1"], evidence_status="EVIDENCE_AVAILABLE",
    )
    row = s.decide(
        organization_id="O1", plant_id="P1", decision_id=row["decision_id"],
        decision="APPROVED", operator_id="operator-7", rationale="Evidence reviewed",
    )
    assert row["decision"] == "APPROVED"
    row = s.record_outcome(
        organization_id="O1", plant_id="P1", decision_id=row["decision_id"],
        outcome="IMPROVED", note="Post-maintenance observation improved",
    )
    assert row["outcome"] == "IMPROVED"
    reopened = DecisionGovernanceStore(path).get(row["decision_id"])
    assert reopened["operator_id"] == "operator-7"
    assert reopened["outcome"] == "IMPROVED"


def test_outcome_requires_human_approval():
    s = store()
    row = s.create(
        organization_id="O1", plant_id="P1", subject_type="EQUIPMENT",
        subject_id="PT-303", recommendation="Inspect transmitter",
        evidence_ids=["obs-1"], evidence_status="EVIDENCE_AVAILABLE",
    )
    with pytest.raises(ValueError, match="HUMAN_DECISION_REQUIRED_BEFORE_OUTCOME"):
        s.record_outcome(
            organization_id="O1", plant_id="P1", decision_id=row["decision_id"],
            outcome="IMPROVED",
        )


def test_tenant_isolation():
    s = store()
    row = s.create(
        organization_id="O1", plant_id="P1", subject_type="EQUIPMENT",
        subject_id="PT-303", recommendation="Review", evidence_ids=["obs-1"],
        evidence_status="EVIDENCE_AVAILABLE",
    )
    with pytest.raises(KeyError, match="DECISION_NOT_FOUND"):
        s.get("missing")
    with pytest.raises(KeyError, match="DECISION_NOT_FOUND"):
        s.decide(
            organization_id="O2", plant_id="P9", decision_id=row["decision_id"],
            decision="APPROVED", operator_id="wrong-tenant",
        )


def test_invalid_decision_and_outcome_rejected():
    s = store()
    row = s.create(
        organization_id="O1", plant_id="P1", subject_type="EQUIPMENT",
        subject_id="PT-303", recommendation="Review", evidence_ids=["obs-1"],
        evidence_status="EVIDENCE_AVAILABLE",
    )
    with pytest.raises(ValueError, match="INVALID_HUMAN_DECISION"):
        s.decide(
            organization_id="O1", plant_id="P1", decision_id=row["decision_id"],
            decision="EXECUTE", operator_id="operator-1",
        )
    assert s.snapshot("O1", "P1")["automatic_execution"] is False
