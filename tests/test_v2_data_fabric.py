from v2.contracts import IndustrialPoint
from v2.data_fabric import ReadOnlyDataFabric, normalize_simulation_point

def point(plant, tag, value, ts):
    return IndustrialPoint(plant_id=plant, tag=tag, timestamp=ts, value=value, source="TEST")

def test_plant_and_tag_scoping():
    fabric = ReadOnlyDataFabric(max_points_per_tag=3)
    fabric.ingest(point("plant-a", "PT-303", 10.0, "t1"))
    fabric.ingest(point("plant-a", "PT-303", 11.0, "t2"))
    fabric.ingest(point("plant-b", "PT-303", 99.0, "t2"))
    assert fabric.latest("plant-a", "PT-303").value == 11.0
    assert fabric.latest("plant-b", "PT-303").value == 99.0
    assert [p.value for p in fabric.history("plant-a", "PT-303")] == [10.0, 11.0]

def test_bounded_history():
    fabric = ReadOnlyDataFabric(max_points_per_tag=2)
    for i in (1, 2, 3):
        fabric.ingest(point("plant-a", "FT-1", i, "t" + str(i)))
    assert [p.value for p in fabric.history("plant-a", "FT-1")] == [2, 3]

def test_safety_contract():
    health = ReadOnlyDataFabric().health("plant-a").to_dict()
    assert health["status"] == "NO_DATA"
    assert health["read_only"] is True
    assert health["plc_write"] is False
    assert health["scada_control"] is False
    assert health["human_decision_required"] is True

def test_existing_simulation_normalization():
    p = normalize_simulation_point(
        {"tag":"PT-303","timestamp":"t1","value":42.5,
         "source":"PCI DEMO STREAM","mode":"SIMULATION","state":"HEALTHY"},
        "plant-a",
    )
    assert p.tag == "PT-303"
    assert p.value == 42.5
    assert p.source == "PCI DEMO STREAM"
    assert p.mode == "SIMULATION"
    assert p.quality == "GOOD"
