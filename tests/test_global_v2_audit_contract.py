from datetime import datetime, timezone
import pytest
from anvi_v2_audit_contract import AuditRecord, AuditLedger

def record(org="o1", plant="p1"):
    return AuditRecord(org, plant, "anvi-service", "OBSERVE", "PT_303",
        datetime(2026, 1, 1, tzinfo=timezone.utc), "ACCEPTED", "corr-1",
        {"read_only": True, "plc_write": False, "scada_control": False,
         "automatic_execution": False, "human_decision_required": True})

def test_append_dedup_and_query():
    ledger = AuditLedger()
    assert ledger.append(record(), "o1", "p1") is True
    assert ledger.append(record(), "o1", "p1") is False
    assert len(ledger.query("o1", "p1")) == 1

def test_foreign_tenant_blocked():
    with pytest.raises(PermissionError):
        AuditLedger().append(record(org="other"), "o1", "p1")

def test_naive_timestamp_blocked():
    r = record()
    r = AuditRecord(r.organization_id, r.plant_id, r.actor, r.action, r.resource,
                    datetime(2026, 1, 1), r.result, r.correlation_id, r.safety_flags)
    with pytest.raises(ValueError):
        r.validate()

def test_audit_safety():
    s = AuditLedger().snapshot()
    assert s["append_only"] is True
    assert s["tenant_scoped"] is True
    assert s["secret_payloads"] is False
    assert s["plc_write"] is False
    assert s["scada_control"] is False
    assert s["automatic_execution"] is False
    assert s["human_decision_required"] is True
