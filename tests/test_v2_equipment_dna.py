from v2.equipment_dna import (
    EquipmentDNAContext,
    EquipmentNode,
    EquipmentRelation,
    nodes_from_points,
)


def test_dna_is_tenant_scoped():
    graph = EquipmentDNAContext()
    graph.add_node(EquipmentNode("A", "PT-303", equipment_type="AI"))
    graph.add_node(EquipmentNode("B", "PT-303", equipment_type="AI"))
    graph.add_relation(EquipmentRelation("A", "PT-303", "feeds", "PIC-1"))

    assert graph.node("A", "PT-303") is not None
    assert graph.node("B", "PT-303") is not None
    assert graph.node("B", "PIC-1") is None
    assert graph.relations("B", "PT-303") == ()


def test_dna_context_contains_supplied_relationships_only():
    graph = EquipmentDNAContext()
    graph.load(
        nodes_from_points(
            [{"tag": "PT-303", "io_type": "AI", "area": "AREA-A"}],
            "A",
        ),
        [EquipmentRelation("A", "PT-303", "measures", "VESSEL-1")],
    )
    context = graph.context("A", "PT-303")
    assert context["evidence_status"] == "FOUND"
    assert context["relations"][0]["relation"] == "measures"


def test_dna_has_no_control_path():
    graph = EquipmentDNAContext()
    result = graph.context("A", "PT-303")
    assert result["plc_write"] is False
    assert result["scada_control"] is False
    assert result["automatic_action"] is False


def test_nodes_from_points_is_generic():
    points = [
        {"tag": "X1", "io_type": "DI", "description": "Any point", "area": "Any area"},
        {"tag": "X2", "io_type": "AI"},
    ]
    nodes = nodes_from_points(points, "PLANT-X")
    assert [x.tag for x in nodes] == ["X1", "X2"]
    assert all(x.plant_id == "PLANT-X" for x in nodes)
