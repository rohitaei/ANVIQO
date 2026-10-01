import industrial_intelligence_platform as iip

def test_full_platform_safety_and_modules():
    r=iip.run_industrial_intelligence({
        "alarms":[{"tag":"PT-303","state":"ACTIVE"}],
        "process_values":[{"tag":"PT-303","value":120}],
        "sensor_samples":[{"tag":"PT-303","value":120,"quality":"GOOD"}]*5,
        "reliability_events":[{"equipment":"PT-303","type":"FAILURE"}],
        "events":[{"tag":"PT-303","type":"DEVIATION"}],
        "gateway_tags":[{"tag":"PT-303","value":120}],
        "energy":[{"value":10,"production":2}],
        "production":[{"production":2,"loss":1}],
        "quality":[{"within_spec":False}],
        "spares":[{"equipment":"PT-303","qty_available":1,"minimum_stock":2}],
        "process_safety":{"interlocks":["IL-1"]},
        "ot_assets":[{"asset":"PLC-1"}],
        "graph_nodes":[{"id":"PT-303"}],
        "graph_relationships":[{"from":"PT-303","to":"PLC-1"}],
        "health_evidence":[{"severity":"HIGH"}],
    })
    assert set(["alarm","process","sensor","reliability","root_cause","energy","production","quality","maintenance","spares","shift","field","procedures","process_safety","ot","graph","incident","health","benchmark","digital_twin","sustainability","governance","gateway"]).issubset(r)
    assert r["safety"]["read_only"] is True
    assert r["safety"]["plc_write"] is False
    assert r["safety"]["scada_control"] is False
    assert r["safety"]["human_decision_required"] is True
    assert r["root_cause"]["causation_established"] is False
    assert r["gateway"]["mode"] == "SIMULATION"

def test_self_test():
    assert iip.self_test()["status"] == "PASS"
