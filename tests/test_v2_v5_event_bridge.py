from v2.equipment_dna import EquipmentDNAContext, EquipmentNode
from v2.event_context import LiveEventContextBridge
from v2.v5_event_bridge import V5EventIntelligenceBridge


def _context(plant_id="PLANT-A", v5=None):
    dna = EquipmentDNAContext()
    dna.add_node(EquipmentNode(plant_id=plant_id, tag="PT-303", area="VRM"))
    watch = {
        "plant_id": plant_id,
        "state": "WATCH",
        "candidates": [{
            "tag": "PT-303",
            "reason": "value_changed_since_previous_observation",
            "previous_value": 10,
            "current_value": 12,
            "trust": "TRUSTED",
            "freshness": "FRESH",
        }],
    }
    return LiveEventContextBridge().build(
        plant_id, watch, dna, v5_what_changed=v5
    )


def test_v5_bridge_invokes_existing_handler_with_v2_context():
    calls = []

    def existing_v5(**kwargs):
        calls.append(kwargs)
        return {"status": "V5_RESULT", "changes": ["PT-303"]}

    context = _context(v5={"status": "PREVIOUS_V5"})
    result = V5EventIntelligenceBridge(existing_v5).run(context)

    assert result["status"] == "INVOKED"
    assert result["plant_id"] == "PLANT-A"
    assert result["result"]["status"] == "V5_RESULT"
    assert calls[0]["plant_id"] == "PLANT-A"
    assert calls[0]["changed_points"][0]["tag"] == "PT-303"
    assert calls[0]["equipment_context"][0]["context"]["node"]["tag"] == "PT-303"
    assert calls[0]["existing_what_changed"]["status"] == "PREVIOUS_V5"


def test_v5_bridge_does_not_invoke_new_reasoning_without_handler():
    context = _context(v5={"status": "EXISTING_V5"})
    result = V5EventIntelligenceBridge().run(context)

    assert result["status"] == "NOT_INVOKED"
    assert result["existing_what_changed"]["status"] == "EXISTING_V5"


def test_v5_bridge_preserves_tenant_scope():
    context = _context("PLANT-B")
    seen = []

    def existing_v5(**kwargs):
        seen.append(kwargs)
        return {"plant_id": kwargs["plant_id"]}

    result = V5EventIntelligenceBridge(existing_v5).run(context)

    assert result["plant_id"] == "PLANT-B"
    assert seen[0]["plant_id"] == "PLANT-B"
    assert seen[0]["equipment_context"][0]["context"]["plant_id"] == "PLANT-B"


def test_v5_bridge_does_not_fallback_to_other_plant():
    dna = EquipmentDNAContext()
    dna.add_node(EquipmentNode(plant_id="PLANT-A", tag="PT-303"))
    watch = {
        "plant_id": "PLANT-B",
        "state": "WATCH",
        "candidates": [{"tag": "PT-303", "reason": "change"}],
    }
    context = LiveEventContextBridge().build("PLANT-B", watch, dna)

    seen = []

    def existing_v5(**kwargs):
        seen.append(kwargs)
        return {"ok": True}

    V5EventIntelligenceBridge(existing_v5).run(context)

    assert seen[0]["equipment_context"][0]["context"] is None
    assert seen[0]["equipment_context"][0]["evidence_status"] == "NO_EQUIPMENT_DNA_CONTEXT"


def test_v5_bridge_preserves_read_only_human_governance():
    context = _context()
    result = V5EventIntelligenceBridge().run(context)

    assert result["safety"] == {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "automatic_action": False,
        "human_decision_required": True,
    }
