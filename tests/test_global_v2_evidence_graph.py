from datetime import datetime, timezone, timedelta
import pytest
from anvi_v2_realtime_store import TelemetryPoint, StreamEvent
from anvi_v2_global_capability_contracts import TenantRef
from anvi_v2_evidence_graph import build_evidence_graph

def test_graph_preserves_tenant_and_no_causal_claim():
    t = TenantRef("o", "p")
    now = datetime(2026,10,5,12,0,tzinfo=timezone.utc)
    p = TelemetryPoint("o","p","PT_303",now,68.0,"bar","GOOD","S7")
    e = StreamEvent("o","p","ALARM",now+timedelta(seconds=5),"High pressure",tag="PT_303")
    g = build_evidence_graph(t,[p],[e])
    assert len(g.nodes) == 2
    assert len(g.edges) == 1
    assert g.causal_claimed is False
    assert g.edges[0].relation == "temporally_associated"

def test_graph_blocks_foreign_tenant():
    t = TenantRef("o","p")
    now = datetime(2026,10,5,12,0,tzinfo=timezone.utc)
    p = TelemetryPoint("x","other","PT_303",now,68.0,"bar","GOOD","S7")
    with pytest.raises(PermissionError):
        build_evidence_graph(t,[p],[])
