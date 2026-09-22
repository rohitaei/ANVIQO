from v2.equipment_dna import EquipmentDNAContext
from v2.pt_pressure_demo import run_pt_pressure_demo
from v2.watch import WatchSnapshot

def test_pt_pressure_demo_is_tenant_scoped_and_read_only():
    w=WatchSnapshot("A","WATCH",1,1,0,0,[{"tag":"PT-303","reason":"VALUE_CHANGED"}],{},{"read_only":True,"plc_write":False,"scada_control":False,"automatic_action":False,"human_decision_required":True})
    package={"plant":{"plant_id":"A"},"records":[{"tag":"PT-303","area":"MILL","metadata":{"health_score":90,"status":"HEALTHY"}}]}
    dna=EquipmentDNAContext()
    seen=[]
    result=run_pt_pressure_demo("A",w,dna,package,lambda p,t: seen.append((p,t)) or {"verified":True},
      v5_builder=lambda p,areas,equipment_events=None: {"plant":p,"areas":areas})
    assert seen==[("A","PT-303")]
    assert result["plant_id"]=="A"
    assert result["human_verification_required"] is True
    assert result["safety"]["scada_control"] is False
