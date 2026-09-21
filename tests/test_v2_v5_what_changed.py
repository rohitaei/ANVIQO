from v2.equipment_dna import EquipmentDNAContext, EquipmentNode
from v2.event_context import LiveEventContextBridge
from v2.v5_what_changed import run_existing_v5_what_changed


def _context(plant_id="PLANT-A"):
    dna = EquipmentDNAContext()
    dna.add_node(EquipmentNode(plant_id=plant_id, tag="PT-303"))
    watch = {
        "plant_id": plant_id,
        "state": "WATCH",
        "candidates": [{"tag": "PT-303", "reason": "change"}],
    }
    return LiveEventContextBridge().build(plant_id, watch, dna)


def test_calls_existing_v5_builder():
    seen = {}

    def existing_v5(plant_name, area_results, equipment_events=None):
        seen["plant_name"] = plant_name
        seen["areas"] = area_results
        seen["events"] = equipment_events
        return {"status": "EXISTING_V5"}

    context = _context()
    areas = [{"plant_id": "PLANT-A", "area": "VRM", "health_score": 80}]
    result = run_existing_v5_what_changed(
        context, areas, equipment_events={"PT-303": []}, v5_builder=existing_v5
    )

    assert result["status"] == "V5_WHAT_CHANGED_COMPLETE"
    assert seen["plant_name"] == "PLANT-A"
    assert seen["areas"] == areas
    assert seen["events"] == {"PT-303": []}


def test_rejects_cross_plant_area_evidence():
    context = _context("PLANT-B")
    areas = [{"plant_id": "PLANT-A", "area": "VRM", "health_score": 80}]

    try:
        run_existing_v5_what_changed(context, areas, v5_builder=lambda *a, **k: {})
    except ValueError as exc:
        assert "plant_id" in str(exc)
    else:
        raise AssertionError("cross-plant evidence must be rejected")


def test_preserves_safety_contract():
    context = _context()
    result = run_existing_v5_what_changed(
        context,
        [{"plant_id": "PLANT-A", "area": "VRM"}],
        v5_builder=lambda *a, **k: {"status": "V5"},
    )

    assert result["safety"] == {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "automatic_action": False,
        "human_decision_required": True,
    }
