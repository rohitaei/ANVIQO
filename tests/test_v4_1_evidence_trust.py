from datetime import datetime, timezone, timedelta
import pytest
from anvi_v4_1_evidence_trust import assess_evidence_trust, connector_readiness, validate_scope, SAFETY

NOW=datetime(2026,10,9,2,30,tzinfo=timezone.utc)
def ev(**kw):
    d={"organization_id":"O","plant_id":"P","source_type":"PLC_EDGE",
       "observed_at":NOW.isoformat(),"quality":"GOOD","lineage":["edge","quality"]}
    d.update(kw);return d

def test_empty_evidence_is_explicit():
    r=assess_evidence_trust([],now=NOW)
    assert r["status"]=="NO_EVIDENCE" and r["trust_score"]==0

def test_high_trust_requires_fresh_good_complete_lineage():
    rows=[ev(),ev(source_type="HISTORIAN",lineage=["historian","quality"])]
    r=assess_evidence_trust(rows,now=NOW)
    assert r["trust_level"]=="HIGHER_TRUST"
    assert r["dimensions"]["freshness"]=="FRESH"
    assert r["causation_claimed"] is False

def test_stale_bad_and_missing_lineage_lower_trust():
    rows=[ev(observed_at=(NOW-timedelta(hours=2)).isoformat(),quality="BAD",lineage=[])]
    r=assess_evidence_trust(rows,now=NOW)
    assert r["trust_level"]=="LOW_TRUST"
    assert r["dimensions"]["freshness"]=="STALE"
    assert r["dimensions"]["lineage"]=="MISSING"

def test_invalid_naive_timestamp_is_unknown():
    r=assess_evidence_trust([ev(observed_at="2026-10-09T02:00:00")],now=NOW)
    assert r["dimensions"]["freshness"]=="UNKNOWN"

def test_trust_score_is_not_probability_or_authorization():
    r=assess_evidence_trust([ev()],now=NOW)
    assert any("not a probability" in x for x in r["limitations"])
    assert r["safety"]["automatic_execution"] is False
    assert r["safety"]["plc_write"] is False

def test_connector_readiness_does_not_claim_live_connection():
    r=connector_readiness({"source_id":"s","organization_id":"O","plant_id":"P","source_type":"OPC_UA"})
    assert r["ready"] and r["live_connection_verified"] is False

def test_connector_write_mode_rejected():
    r=connector_readiness({"source_id":"s","organization_id":"O","plant_id":"P","source_type":"SAP","read_only":False})
    assert not r["ready"] and "read_only=true" in r["missing"]

def test_unknown_connector_rejected():
    assert connector_readiness({"source_type":"MAGIC_PLC"})["status"]=="UNSUPPORTED"

def test_scope_rejects_cross_plant_and_tenant():
    with pytest.raises(PermissionError,match="PLANT_BOUNDARY"):
        validate_scope([ev(plant_id="P2")],"O","P")
    with pytest.raises(PermissionError,match="TENANT_BOUNDARY"):
        validate_scope([ev(organization_id="X")],"O","P")

def test_policy_parameters_validated():
    with pytest.raises(ValueError): assess_evidence_trust([ev()],now=NOW,stale_after_seconds=-1)
    with pytest.raises(ValueError): assess_evidence_trust([ev()],now=datetime(2026,10,9))
