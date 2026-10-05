from datetime import datetime, timezone
import pytest
from anvi_v2_prediction_validation import AnomalyAssessment, PredictionOutcome, drift_signal
from anvi_v2_causal_reasoning import build_hypothesis
from anvi_v2_integration_gateway import IntegrationEnvelope, dispatch

def tenant():
    return type('T', (), {'organization_id':'o1','plant_id':'p1'})()

def test_prediction_validation_and_drift():
    a=AnomalyAssessment(tenant(),'a1',datetime.now(timezone.utc),.8,.7,.9,('e1',)); a.validate()
    assert drift_signal(.8,.5,.2)
    p=PredictionOutcome(tenant(),'p1',datetime.now(timezone.utc),datetime.now(timezone.utc),10,12,2); p.validate()

def test_causal_hypothesis_requires_evidence_and_review():
    h=build_hypothesis(tenant(),'h1','n1','n2',.8,['e1']); assert h.human_review_required and not h.causal_claimed
    with pytest.raises(ValueError): build_hypothesis(tenant(),'h2','n1','n2',1.2,['e1'])

def test_ot_integration_is_dry_run_and_write_blocked():
    e=IntegrationEnvelope(tenant(),'S7','read_telemetry',{'tag':'PT_303'})
    assert dispatch(e)['dry_run'] is True
    with pytest.raises(PermissionError): dispatch(IntegrationEnvelope(tenant(),'S7','write',{},False))

def test_unknown_integration_fails_closed():
    with pytest.raises(ValueError): dispatch(IntegrationEnvelope(tenant(),'UNKNOWN','x',{}))
