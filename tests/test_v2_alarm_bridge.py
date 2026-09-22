from v2.alarm_bridge import run_alarm_bridge

def test_alarm_bridge_preserves_explicit_alarm_only():
    r=run_alarm_bridge("A",[{"tag":"PT-1","state":"HIGH"}])
    assert r["status"]=="NOT_INVOKED"
    assert r["alarms"][0]["plant_id"]=="A"
    assert r["safety"]["plc_write"] is False

def test_alarm_bridge_rejects_cross_plant():
    try: run_alarm_bridge("A",[{"plant_id":"B","tag":"PT-1"}])
    except ValueError: pass
    else: raise AssertionError("cross-plant alarm accepted")

def test_alarm_bridge_forwards_existing_handler():
    seen=[]
    r=run_alarm_bridge("A",[{"tag":"PT-1"}],lambda p,a: seen.append((p,a)) or {"ok":True})
    assert r["status"]=="INVOKED"
    assert seen[0][0]=="A"
