from dataclasses import dataclass

from v2.equipment_dna import EquipmentDNAContext, EquipmentNode
from v2.event_context import LiveEventContextBridge


@dataclass
class Candidate:
    tag: str
    reason: str
    previous_value: float
    current_value: float
    trust: str = "TRUSTED"
    freshness: str = "FRESH"


@dataclass
class Watch:
    plant_id: str
    state: str
    candidates: list


def test_live_event_bridge_joins_watch_to_equipment_dna():
    dna = EquipmentDNAContext()
    dna.add_node(
        EquipmentNode(
            plant_id="PLANT-A",
            tag="PT-303",
            equipment_type="PRESSURE_TRANSMITTER",
            area="VRM",
        )
    )
    watch = Watch(
        plant_id="PLANT-A",
        state="WATCH",
        candidates=[
            Candidate("PT-303", "VALUE_CHANGED", 10, 12),
        ],
    )

    result = LiveEventContextBridge().build("PLANT-A", watch, dna)

    assert result.state == "WATCH"
    assert result.changed_points[0]["tag"] == "PT-303"
    assert result.equipment_context[0]["evidence_status"] == "EQUIPMENT_DNA_CONTEXT"
    assert result.equipment_context[0]["context"]["node"]["tag"] == "PT-303"


def test_live_event_bridge_is_tenant_scoped():
    dna = EquipmentDNAContext()
    dna.add_node(EquipmentNode(plant_id="PLANT-A", tag="PT-303"))
    dna.add_node(EquipmentNode(plant_id="PLANT-B", tag="PT-303"))

    watch = Watch(
        plant_id="PLANT-B",
        state="WATCH",
        candidates=[Candidate("PT-303", "VALUE_CHANGED", 1, 2)],
    )

    result = LiveEventContextBridge().build("PLANT-B", watch, dna)

    node = result.equipment_context[0]["context"]["node"]
    assert node["plant_id"] == "PLANT-B"


def test_live_event_bridge_does_not_fallback_across_plants():
    dna = EquipmentDNAContext()
    dna.add_node(EquipmentNode(plant_id="PLANT-A", tag="PT-303"))

    watch = Watch(
        plant_id="PLANT-B",
        state="WATCH",
        candidates=[Candidate("PT-303", "VALUE_CHANGED", 1, 2)],
    )

    result = LiveEventContextBridge().build("PLANT-B", watch, dna)

    assert result.equipment_context[0]["context"] is None
    assert result.equipment_context[0]["evidence_status"] == "NO_EQUIPMENT_DNA_CONTEXT"


def test_live_event_bridge_preserves_existing_v5_result_without_reimplementing_it():
    v5_result = {"status": "EXISTING_V5_RESULT", "changes": ["PT-303 changed"]}

    result = LiveEventContextBridge().build(
        "PLANT-A",
        {"state": "WATCH", "candidates": []},
        EquipmentDNAContext(),
        v5_what_changed=v5_result,
    )

    assert result.v5_what_changed is v5_result


def test_live_event_bridge_safety_contract():
    result = LiveEventContextBridge().build(
        "PLANT-A",
        {"state": "INSUFFICIENT_EVIDENCE", "candidates": []},
        EquipmentDNAContext(),
    )

    assert result.safety == {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "automatic_action": False,
        "human_decision_required": True,
    }
