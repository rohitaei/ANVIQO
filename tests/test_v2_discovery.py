from v2.discovery import discover
from v2.watch import WatchSnapshot

def s(p):
    return WatchSnapshot(p,"WATCH",1,1,0,0,[{"tag":"PT-303","reason":"VALUE_CHANGED"}],{},{"read_only":True,"plc_write":False,"scada_control":False,"automatic_action":False,"human_decision_required":True})

def test_discovery_is_not_alarm_or_diagnosis():
    r=discover("A",s("A"))
    assert r["candidates"][0]["classification"]=="DISCOVERY_CANDIDATE"
    assert r["candidates"][0]["is_alarm"] is False
    assert r["candidates"][0]["is_diagnosis"] is False

def test_discovery_rejects_cross_plant():
    try: discover("A",s("B"))
    except ValueError: pass
    else: raise AssertionError("cross-plant discovery accepted")
