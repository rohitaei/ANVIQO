from datetime import datetime, timedelta, timezone
from anvi_v2_realtime_store import TelemetryPoint, StreamEvent
from anvi_v3_1_real_time_evidence import assess_observations, build_evidence_chain

def test_detects_stale_missing_and_bad_quality():
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    rows = [
        TelemetryPoint("o","p","PT-1",now-timedelta(minutes=10),10.0,quality="GOOD",source="SIM"),
        TelemetryPoint("o","p","PT-2",now-timedelta(seconds=10),20.0,quality="BAD",source="SIM"),
    ]
    result = assess_observations(rows, expected_tags=["PT-1","PT-2","PT-3"], now=now, stale_after_seconds=300)
    assert result["stale_tags"] == ["PT-1"]
    assert result["missing_tags"] == ["PT-3"]
    assert result["weak_evidence_tags"] == ["PT-1","PT-2"]

def test_duplicate_detection_is_explicit():
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    point = TelemetryPoint("o","p","PT-1",now,10.0,quality="GOOD",source="SIM")
    result = assess_observations([point, point], now=now)
    assert result["observations"][0]["duplicate_count"] == 1
    assert result["observations"][0]["evidence_strength"] == "WEAK"

def test_evidence_chain_is_association_not_causation():
    now = datetime(2026, 10, 7, tzinfo=timezone.utc)
    point = TelemetryPoint("o","p","PT-1",now,68.0,source="SIM")
    event = StreamEvent("o","p","ALARM",now+timedelta(seconds=20),"warning","PT-1",severity="WARNING",source="SIM").normalized()
    result = build_evidence_chain([point],[event],tag="PT-1")
    assert len(result["links"]) == 1
    assert result["links"][0]["relationship"] == "temporally_associated"
    assert result["causal_claimed"] is False
