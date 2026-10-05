from datetime import datetime, timezone
import pytest
from anvi_v2_edge_ingestion_bridge import EdgeIngestionBridge
from anvi_v2_secure_edge_runtime import EdgeEnvelope

def env(seq=1, protocol="S7", org="o1", plant="p1", ts=None):
    return EdgeEnvelope(org, plant, protocol, seq, ts or datetime(2026, 1, 1, tzinfo=timezone.utc), {"source_address": "192.168.0.166"})

def test_supported_edge_is_normalized_and_stored():
    b = EdgeIngestionBridge()
    assert b.ingest(env(), "o1", "p1", "PT_303", 68.0, "GOOD", "bar") is True
    rows = b.time_series.query("o1", "p1", datetime(2025, 12, 31, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc), "PT_303")
    assert len(rows) == 1
    assert rows[0].value == 68.0
    assert rows[0].sequence == 1

def test_duplicate_edge_is_not_ingested_twice():
    b = EdgeIngestionBridge()
    assert b.ingest(env(), "o1", "p1", "PT_303", 42.0) is True
    assert b.ingest(env(), "o1", "p1", "PT_303", 43.0) is False

def test_foreign_and_unsupported_inputs_fail_closed():
    b = EdgeIngestionBridge()
    with pytest.raises(PermissionError):
        b.ingest(env(org="other"), "o1", "p1", "PT_303", 42.0)
    with pytest.raises(ValueError):
        b.ingest(env(protocol="UNKNOWN"), "o1", "p1", "PT_303", 42.0)

def test_naive_timestamp_blocked():
    b = EdgeIngestionBridge()
    with pytest.raises(ValueError):
        b.ingest(env(ts=datetime(2026, 1, 1)), "o1", "p1", "PT_303", 42.0)

def test_safety_has_no_control_path():
    safety = EdgeIngestionBridge().safety()
    assert safety["outbound_only"] is True
    assert safety["read_only"] is True
    assert safety["plc_write"] is False
    assert safety["scada_control"] is False
    assert safety["automatic_execution"] is False
    assert safety["human_decision_required"] is True
    assert safety["control_path"] == "NONE"
