import industrial_intelligence_platform as iip

MODULES={"alarm","process","sensor","reliability","root_cause","energy","production","quality","maintenance","spares","shift","field","procedures","process_safety","ot","graph","incident","health","benchmark","digital_twin","sustainability","governance","gateway"}

def payload():
    return {
        "alarms":[
            {"tag":"PT-303","state":"ACTIVE","timestamp":"2026-01-01T00:00:00+00:00"},
            {"tag":"PT-303","state":"ACTIVE","timestamp":"2026-01-01T00:00:30+00:00"},
            {"tag":"PT-303","state":"ACTIVE","timestamp":"2026-01-01T00:01:00+00:00"},
            {"tag":"PT-303","state":"ACTIVE","timestamp":"2026-01-01T00:01:30+00:00"},
            {"tag":"PT-402","state":"ACTIVE","stale":True}],
        "process_values":[{"tag":"PT-303","value":80},{"tag":"PT-303","value":125}],
        "envelopes":{"PT-303":{"min":90,"max":120}},
        "sensor_samples":[{"tag":"PT-303","value":120,"quality":"GOOD"}]*4+[{"tag":"PT-303","value":120,"quality":"GOOD","calibration_due":True}],
        "reliability_events":[{"equipment":"PT-303","type":"FAILURE"},{"equipment":"PT-303","type":"REPAIR","duration_hours":2},{"equipment":"PT-303","type":"TRIP"}],
        "observation_hours":100,
        "events":[{"tag":"PT-303","type":"DEVIATION"}],
        "energy":[{"value":100,"production":20,"abnormal":True}],
        "production":[{"production":20,"loss":3}],
        "quality":[{"within_spec":False}],
        "maintenance":[{"equipment":"PT-303","event":"repair"}],
        "spares":[{"equipment":"PT-303","qty_available":1,"minimum_stock":2,"used":True}],
        "shift":{"abnormal_equipment":["PT-303"],"alarms":["PT-303"],"maintenance":["repair"],"spares_used":["PT-303 x1"],"open_issues":["verify"],"follow_up":["next shift"]},
        "field":[{"equipment":"PT-303","observation":"abnormal pressure"}],
        "procedures":[{"title":"PT-303 calibration","text":"calibration verification procedure"}],
        "procedure_query":"calibration",
        "process_safety":{"interlocks":["IL-1"],"permissives":["P-1"],"safeguards":["S-1"],"critical_conditions":["HIGH PRESSURE"]},
        "ot_assets":[{"asset":"PLC-1"}],
        "graph_nodes":[{"id":"PT-303"},{"id":"PLC-1"}],
        "graph_relationships":[{"from":"PT-303","to":"PLC-1"}],
        "incident_events":[{"tag":"PT-303","type":"DEVIATION"}],
        "health_evidence":[{"severity":"HIGH"}],
        "benchmark":[{"plant":"A","metric":"availability","value":95}],
        "identity":{"equipment":"PT-303","area":"VRM/MILL","tag":"PT-303"},
        "condition":{"state":"WARNING"},"history":[{"value":110},{"value":120}],"prediction":{"state":"RISING"},
        "sustainability":[{"energy":100,"production":20,"emissions":5}],
        "governance_evidence":[{"source":"sim","quality":"GOOD"}],
        "gateway_tags":[{"tag":"PT-303","value":120}]}

def test_every_functional_path_and_safety_boundary():
    r=iip.run_industrial_intelligence(payload())
    assert MODULES <= set(r)
    assert r["version"]==iip.VERSION
    assert r["alarm"]["recurring"] and r["alarm"]["chattering"] and r["alarm"]["stale"]
    assert r["process"]["deviations"] and r["sensor"]["issues"]
    assert r["reliability"]["failures"]==2
    assert r["root_cause"]["causation_established"] is False
    assert r["energy"]["specific_energy"]==5
    assert r["production"]["loss_total"]==3 and r["quality"]["out_of_spec"]==1
    assert r["maintenance"]["history_count"]==1 and r["spares"]["stock_risk"]
    assert r["shift"]["evidence_backed"] and r["field"]["verification_status"]=="PENDING_VERIFICATION"
    assert r["procedures"]["matches"] and r["process_safety"]["control_independence"]
    assert r["ot"]["approved_paths_only"] and r["graph"]["auditable"]
    assert r["incident"]["causation_established"] is False
    assert r["health"]["score"] is not None and r["benchmark"]["records"]==1
    assert r["digital_twin"]["identity"]["equipment"]=="PT-303"
    assert r["sustainability"]["records"]==1 and r["governance"]["human_approval_required"]
    assert r["gateway"]["mode"]=="SIMULATION"
    for name in MODULES:
        s=r[name]["safety"]
        assert s["read_only"] is True and s["plc_write"] is False and s["scada_control"] is False
        assert s["human_decision_required"] is True and s["automatic_authorization"] is False and s["automatic_execution"] is False

def test_empty_input_path_is_safe():
    r=iip.run_industrial_intelligence({})
    assert MODULES <= set(r)
    assert r["safety"]==iip.SAFETY and r["gateway"]["mode"]=="SIMULATION" and r["health"]["score"] is None
