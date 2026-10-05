from datetime import datetime, timezone

import pytest

from anvi_v2_global_capability_contracts import (
    TenantRef, AuditRecord, PredictionValidation, CausalEdge,
    DigitalTwinState, WhatIfScenario, IntegrationRequest, OutcomeRecord,
    BenchmarkRecord, ResilienceCheck, assert_tenant, safety_contract,
    capability_surface,
)

def t():
    return TenantRef("org-a", "plant-a")

def test_complete_v2_surface_is_declared():
    surface = capability_surface()
    assert len(surface) == 20
    assert surface["advanced_replay"] == "implemented"

def test_safety_contract_is_read_only():
    s = safety_contract()
    assert s["read_only"] is True
    assert s["plc_write"] is False
    assert s["scada_control"] is False
    assert s["automatic_execution"] is False
    assert s["human_decision_required"] is True

def test_tenant_boundary():
    with pytest.raises(PermissionError):
        assert_tenant(t(), TenantRef("org-b", "plant-b"))

def test_audit_and_prediction_validation():
    now = datetime.now(timezone.utc)
    AuditRecord(t(), "u1", "ASK_ANVI", now, "ALLOWED", "c1").validate()
    PredictionValidation(t(), "m1", "p1", now, 60, .8, False).validate()

def test_causal_confidence_is_bounded():
    with pytest.raises(ValueError):
        CausalEdge(t(), "a", "b", "associated_with", 1.5).validate()

def test_external_integration_defaults_to_dry_run():
    req = IntegrationRequest(t(), "SAP", "CREATE_WORK_ORDER", {})
    assert req.dry_run is True

def test_models_are_tenant_scoped():
    now = datetime.now(timezone.utc)
    assert DigitalTwinState(t(), "asset", now, {}, "simulation").tenant == t()
    assert WhatIfScenario(t(), "s1", {}, {}).tenant == t()
    assert OutcomeRecord(t(), "o1", "d1", "verified", now, True).tenant == t()
    assert BenchmarkRecord(t(), "availability", 99.0, "2026-Q4").tenant == t()
    assert ResilienceCheck("backup_restore", True).passed
