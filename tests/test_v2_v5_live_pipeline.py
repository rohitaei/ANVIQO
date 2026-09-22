from v2.equipment_dna import EquipmentDNAContext, EquipmentNode, EquipmentRelation
from v2.event_context import LiveEventContext
from v2.v5_live_pipeline import run_live_v5_pipeline
from v2.watch import WatchSnapshot


def watch(plant):
    return WatchSnapshot(
        plant_id=plant,
        state="WATCH",
        points_seen=1,
        trusted_points=1,
        limited_points=0,
        untrusted_points=0,
        candidates=[{
            "tag": "PT-303",
            "reason": "VALUE_CHANGED",
            "previous_value": 10,
            "current_value": 12,
            "trust": "TRUSTED",
            "freshness": "FRESH",
        }],
        discovery={},
        safety={
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "automatic_action": False,
            "human_decision_required": True,
        },
    )


def test_pipeline_joins_watch_dna_and_existing_v5():
    dna = EquipmentDNAContext()
    dna.add_node(EquipmentNode(
        plant_id="PLANT-A",
        tag="PT-303",
        equipment_type="TRANSMITTER",
    ))
    dna.add_relation(EquipmentRelation(
        plant_id="PLANT-A",
        source_tag="PT-303",
        relation="MEASURES",
        target_tag="MILL",
    ))

    calls = []

    def provider(plant_id):
        calls.append(plant_id)
        return [{"plant_id": plant_id, "area": "MILL", "health_score": 90,
                 "status": "HEALTHY", "equipment": []}]

    def v5(plant, areas, equipment_events=None):
        return {"plant": plant, "areas": areas}

    result = run_live_v5_pipeline(
        "PLANT-A", watch("PLANT-A"), dna, provider, v5_builder=v5
    )
    assert calls == ["PLANT-A"]
    assert result["result"]["plant"] == "PLANT-A"
    assert result["safety"]["plc_write"] is False


def test_pipeline_rejects_cross_plant_watch():
    dna = EquipmentDNAContext()
    try:
        run_live_v5_pipeline(
            "PLANT-A", watch("PLANT-B"), dna,
            lambda plant: [], v5_builder=lambda *a, **k: {}
        )
    except ValueError as exc:
        assert "plant_id" in str(exc)
    else:
        raise AssertionError("cross-plant watch was accepted")


def test_pipeline_has_no_global_fallback():
    dna = EquipmentDNAContext()
    seen = []
    result = run_live_v5_pipeline(
        "PLANT-B", watch("PLANT-B"), dna,
        lambda plant: (seen.append(plant) or []),
        v5_builder=lambda plant, areas, equipment_events=None: {"plant": plant, "areas": areas}
    )
    assert seen == ["PLANT-B"]
    assert result["result"]["areas"] == []
