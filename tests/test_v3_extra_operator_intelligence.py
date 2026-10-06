from datetime import datetime, timezone, timedelta
from anvi_v2_realtime_store import TelemetryPoint
from anvi_v3_unified_platform import UnifiedIndustrialPlatform, PlatformEvent, SAFETY as V3_SAFETY
from anvi_v3_extra_operator_intelligence import ExtraordinaryOperatorIntelligence, SAFETY

def pt(org,plant,tag,value,minute):
    return TelemetryPoint(org,plant,tag,datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=minute),value,"bar","GOOD","TEST",minute)

def test_all_extra_capabilities_and_safety():
    p=UnifiedIndustrialPlatform(); org="o1"; plant="p1"
    p.ingest(pt(org,plant,"PT-303",42,1),selected_org=org,selected_plant=plant)
    p.ingest(pt(org,plant,"PT-303",55,2),selected_org=org,selected_plant=plant)
    p.ingest(pt(org,plant,"PT-303",68,3),selected_org=org,selected_plant=plant)
    p.add_event(PlatformEvent(org,plant,"ALARM","PT-303",datetime(2026,1,1,0,3,tzinfo=timezone.utc),"PT-303 warning","WARNING","TEST","PT-303"),selected_org=org,selected_plant=plant)
    e=ExtraordinaryOperatorIntelligence(p)
    assert e.attention_now(org,plant)["items"]
    assert e.plant_story(org,plant,"PT-303")["timeline"]
    assert e.time_machine(org,plant,"2026-01-01T00:00:00+00:00","2026-01-01T01:00:00+00:00","PT-303")["telemetry"]
    assert e.plant_memory(org,plant,"PT-303")["history_available"]
    assert e.anomaly_search(org,plant)["anomalies"]
    assert e.deterioration(org,plant,"PT-303")["trend"]=="INCREASING"
    assert e.early_warning(org,plant,"PT-303")["early_warning"]
    assert e.recovery(org,plant,"PT-303")["evidence_status"]=="EVIDENCE_AVAILABLE"
    assert e.what_if(org,plant,"PT-303")["simulation_only"]
    assert e.instrument_health(org,plant,"PT-303")["status"]=="OK"
    assert e.spare_intelligence(org,plant)["human_approval_required"]
    assert e.energy_intelligence(org,plant,["PT-303"])["status"]=="OK"
    assert e.safety_intelligence(org,plant)["critical_alarms"]==0
    assert e.ot_data_trust(org,plant)["telemetry_trust"]=="AVAILABLE"
    assert e.confidence(org,plant,"PT-303")["evidence_strength"]=="HIGH"
    for key,val in SAFETY.items(): assert val is True if key=="read_only" or key=="human_decision_required" else val is False
    assert V3_SAFETY["plc_write"] is False and V3_SAFETY["scada_control"] is False

def test_tenant_isolation():
    p=UnifiedIndustrialPlatform(); e=ExtraordinaryOperatorIntelligence(p)
    p.ingest(pt("o1","p1","A",1,1),selected_org="o1",selected_plant="p1")
    p.ingest(pt("o2","p2","A",99,1),selected_org="o2",selected_plant="p2")
    assert e.confidence("o1","p1")["evidence_count"]==1
    assert e.confidence("o2","p2")["evidence_count"]==1
