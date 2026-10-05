from datetime import datetime, timezone
import pytest
from anvi_v2_secure_edge_runtime import EdgeEnvelope, SecureEdgeBuffer

def e(seq, org="o1", plant="p1", ts=None):
    return EdgeEnvelope(org,plant,"S7",seq,ts or datetime(2026,1,1,tzinfo=timezone.utc),{"tag":"PT_303","value":42})

def test_buffer_dedup_and_ordered_drain():
    b=SecureEdgeBuffer(); assert b.receive(e(2), "o1","p1"); assert b.receive(e(1), "o1","p1"); assert not b.receive(e(1), "o1","p1")
    assert [x.sequence for x in b.drain("o1","p1")] == [1,2]

def test_foreign_and_naive_blocked():
    with pytest.raises(PermissionError): SecureEdgeBuffer().receive(e(1,org="other"),"o1","p1")
    with pytest.raises(ValueError): SecureEdgeBuffer().receive(e(1,ts=datetime(2026,1,1)),"o1","p1")

def test_outbound_only_safety():
    assert SecureEdgeBuffer().control_surface()["outbound_only"] is True
    assert SecureEdgeBuffer().control_surface()["plc_write"] is False
    assert SecureEdgeBuffer().control_surface()["scada_control"] is False
