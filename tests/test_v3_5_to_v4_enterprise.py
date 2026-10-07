import pytest
from anvi_v3_5_to_v4_enterprise import EnterpriseEvidenceStore,V4EnterpriseIntelligence,IntegrationSource,SAFETY,SOURCES

def E(tmp): return V4EnterpriseIntelligence(EnterpriseEvidenceStore(str(tmp/"db")))
def body(**kw):
    x={"evidence_id":"e1","source_id":"edge","source_type":"PLC_EDGE","subject_id":"PT-303","observed_at":"2026-10-08T00:00:00Z","payload":{"value":42},"lineage":["edge","quality"]}
    x.update(kw);return x

def test_v4_summary_and_safety(tmp_path):
    r=E(tmp_path).summary("O","P")
    assert r["version"].startswith("V4.0")
    assert all(SAFETY[k] is v for k,v in {"read_only":True,"plc_write":False,"scada_control":False,"automatic_execution":False}.items())
    assert all(r["milestones"].values())

def test_read_only_source(tmp_path):
    e=E(tmp_path)
    assert e.register_source("O","P",{"source_id":"sap","source_type":"SAP"})["status"]=="REGISTERED"
    with pytest.raises(PermissionError): e.store.register_source(IntegrationSource("x","SAP","O","P",read_only=False))

def test_lineage_and_dedup(tmp_path):
    e=E(tmp_path)
    with pytest.raises(ValueError,match="LINEAGE"): e.federate("O","P",body(lineage=[]))
    assert not e.federate("O","P",body())["deduplicated"]
    assert e.federate("O","P",body())["deduplicated"]

def test_context_corroboration(tmp_path):
    e=E(tmp_path);e.federate("O","P",body())
    e.federate("O","P",body(evidence_id="e2",source_id="sap",source_type="SAP",payload={"wo":"1"},lineage=["sap","operator"]))
    r=e.context("O","P","PT-303")
    assert r["evidence_count"]==2 and r["corroboration"] and not r["causal_claimed"]

def test_tenant_plant_isolation(tmp_path):
    e=E(tmp_path);e.federate("O","P1",body())
    assert e.store.search("O","P2")["count"]==0 and e.store.search("X","P1")["count"]==0
    with pytest.raises(KeyError): e.store.get("X","P1","e1")

def test_audit_durable(tmp_path):
    e=E(tmp_path);e.register_source("O","P",{"source_id":"api","source_type":"API"})
    e.federate("O","P",body(source_id="api",source_type="API"))
    assert e.store.audit_list("O","P")["count"]>=2
    assert EnterpriseEvidenceStore(str(tmp_path/"db")).audit_list("O","P")["count"]>=2

def test_fleet_boundary(tmp_path):
    e=E(tmp_path)
    r=e.benchmark("O",[{"organization_id":"O","plant_id":"P1"},{"organization_id":"O","plant_id":"P2"}])
    assert len(r["plants"])==2 and not r["causal_claimed"] and not r["cross_plant_fallback"]
    with pytest.raises(PermissionError):e.benchmark("O",[{"organization_id":"X","plant_id":"P3"}])

def test_hadr(tmp_path):
    r=E(tmp_path).hadr("O","P")
    assert r["backup_required"] and r["restore_test_required"] and not r["failover_automation_claimed"]

def test_supported_sources():
    assert {"SAP","CMMS","HISTORIAN","OPC_UA","MQTT","MODBUS_TCP"}<=SOURCES
