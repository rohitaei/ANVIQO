"""Universal V2 Equipment DNA / relationship context.

This is a context-normalization layer, not a new intelligence engine.
It represents relationships supplied by plant data and exposes a small,
plant-scoped context object to existing V5 intelligence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


@dataclass(frozen=True)
class EquipmentNode:
    plant_id: str
    tag: str
    equipment_type: Optional[str] = None
    description: Optional[str] = None
    area: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plant_id": self.plant_id,
            "tag": self.tag,
            "equipment_type": self.equipment_type,
            "description": self.description,
            "area": self.area,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class EquipmentRelation:
    plant_id: str
    source_tag: str
    relation: str
    target_tag: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plant_id": self.plant_id,
            "source_tag": self.source_tag,
            "relation": self.relation,
            "target_tag": self.target_tag,
            "metadata": dict(self.metadata),
        }


class EquipmentDNAContext:
    """In-memory, tenant-scoped graph context built from supplied data."""

    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, EquipmentNode]] = {}
        self._relations: Dict[str, list[EquipmentRelation]] = {}

    @staticmethod
    def _plant(plant_id: str) -> str:
        value = str(plant_id or "").strip()
        if not value:
            raise ValueError("plant_id is required")
        return value

    @staticmethod
    def _tag(tag: str) -> str:
        value = str(tag or "").strip()
        if not value:
            raise ValueError("tag is required")
        return value

    def add_node(self, node: EquipmentNode) -> None:
        plant = self._plant(node.plant_id)
        tag = self._tag(node.tag)
        if plant != node.plant_id:
            raise ValueError("node plant_id is invalid")
        self._nodes.setdefault(plant, {})[tag] = node

    def add_relation(self, relation: EquipmentRelation) -> None:
        plant = self._plant(relation.plant_id)
        source = self._tag(relation.source_tag)
        target = self._tag(relation.target_tag)
        if source == target:
            raise ValueError("self-relation is not allowed")
        if plant != relation.plant_id:
            raise ValueError("relation plant_id is invalid")
        self._relations.setdefault(plant, []).append(relation)

    def load(self, nodes: Iterable[EquipmentNode] = (), relations: Iterable[EquipmentRelation] = ()) -> None:
        for node in nodes:
            self.add_node(node)
        for relation in relations:
            self.add_relation(relation)

    def node(self, plant_id: str, tag: str) -> Optional[EquipmentNode]:
        plant = self._plant(plant_id)
        tag = self._tag(tag)
        return self._nodes.get(plant, {}).get(tag)

    def relations(self, plant_id: str, tag: Optional[str] = None) -> Tuple[EquipmentRelation, ...]:
        plant = self._plant(plant_id)
        if tag is None:
            return tuple(self._relations.get(plant, ()))
        tag = self._tag(tag)
        return tuple(
            r for r in self._relations.get(plant, ())
            if r.source_tag == tag or r.target_tag == tag
        )

    def context(self, plant_id: str, tag: str) -> Dict[str, Any]:
        plant = self._plant(plant_id)
        tag = self._tag(tag)
        node = self.node(plant, tag)
        rels = self.relations(plant, tag)
        return {
            "plant_id": plant,
            "tag": tag,
            "node": node.to_dict() if node else None,
            "relations": [r.to_dict() for r in rels],
            "evidence_status": "FOUND" if node or rels else "NO_CONTEXT",
            "source": "V2_EQUIPMENT_DNA_CONTEXT",
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "automatic_action": False,
            "human_decision_required": True,
        }

    def snapshot(self, plant_id: str) -> Dict[str, Any]:
        plant = self._plant(plant_id)
        return {
            "plant_id": plant,
            "nodes": [n.to_dict() for n in self._nodes.get(plant, {}).values()],
            "relations": [r.to_dict() for r in self._relations.get(plant, ())],
            "node_count": len(self._nodes.get(plant, {})),
            "relation_count": len(self._relations.get(plant, ())),
        }


def nodes_from_points(points: Iterable[Mapping[str, Any]], plant_id: str) -> Tuple[EquipmentNode, ...]:
    """Create neutral equipment identity context from normalized point metadata."""
    plant = EquipmentDNAContext._plant(plant_id)
    result = []
    for point in points:
        tag = str(point.get("tag") or "").strip()
        if not tag:
            continue
        result.append(
            EquipmentNode(
                plant_id=plant,
                tag=tag,
                equipment_type=point.get("io_type"),
                description=point.get("description"),
                area=point.get("area"),
                metadata={
                    "source": point.get("source"),
                    "plc_address": point.get("plc_address"),
                    "unit": point.get("unit"),
                },
            )
        )
    return tuple(result)
