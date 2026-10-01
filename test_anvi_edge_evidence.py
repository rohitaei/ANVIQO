from unittest.mock import patch
import anvi_edge_evidence as evidence

def test_state_is_selected_plant_scoped():
    rows=[{"observation_id":"o1","organization_id":"O1","plant_id":"P1","gateway_id":"G1","tag":"PT-303",
           "value":42.5,"timestamp":"2026-10-01T00:00:00Z","quality":"GOOD","source":"ANVIQO_EDGE",
           "protocol":"SIEMENS_S7","received_at":"2026-10-01T00:00:01Z"}]
    with patch.object(evidence,"_rows",return_value=rows):
        result=evidence.state("P1","O1","PT-303")
    assert result["status"]=="AVAILABLE" and result["plant_id"]=="P1"
    assert result["observation_count"]==1
    assert result["safety"]["plc_write"] is False and result["safety"]["scada_control"] is False

def test_missing_scope_fails_closed():
    with patch.object(evidence,"_rows",return_value=[]):
        result=evidence.state("","O1","PT-303")
    assert result["status"]=="NO_EVIDENCE"
