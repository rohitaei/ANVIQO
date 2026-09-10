"""ANVIQO Universal Industrial Onboarding V1.

Configuration/data adapter only. The module converts plant-supplied asset,
instrument, relationship and evidence records into one stable onboarding
contract so the existing V5 intelligence can remain unchanged.

Principle: CHANGE DATA, NOT CODE.

This module never writes PLC/SCADA state, executes actions, or creates a
second reasoning engine. It validates and normalizes supplied plant data;
the existing intelligence layer remains the consumer.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Mapping


ONBOARDING_VERSION = "ANVIQO-ONBOARDING-V1"
SAFETY = {
    "read_only_intelligence": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


@dataclass(frozen=True)
class PlantIdentity:
    organization_id: str
    plant_id: str
    name: str
    industry: str = ""
    timezone: str = "Asia/Kolkata"


@dataclass(frozen=True)
class OnboardingRecord:
    record_type: str
    external_id: str
    name: str = ""
    area: str = ""
    service: str = ""
    asset_type: str = ""
    tag: str = ""
    parent_id: str = ""
    source: str = ""
    metadata: Dict[str, Any] | None = None


def _text(value: Any) -> str:
    return str(value or "").strip()


def normalize_record(raw: Mapping[str, Any], record_type: str) -> OnboardingRecord:
    """Normalize common plant-data column names without changing semantics."""
    rid = _text(raw.get("external_id") or raw.get("id") or raw.get("tag") or raw.get("asset_id"))
    if not rid:
        raise ValueError("external_id, id, tag or asset_id is required")
    return OnboardingRecord(
        record_type=_text(record_type).upper(),
        external_id=rid,
        name=_text(raw.get("name") or raw.get("description") or raw.get("equipment_name")),
        area=_text(raw.get("area") or raw.get("unit") or raw.get("location")),
        service=_text(raw.get("service") or raw.get("process_service")),
        asset_type=_text(raw.get("asset_type") or raw.get("type") or raw.get("instrument_type")),
        tag=_text(raw.get("tag") or raw.get("tag_name")),
        parent_id=_text(raw.get("parent_id") or raw.get("parent") or raw.get("equipment_id")),
        source=_text(raw.get("source") or raw.get("document") or raw.get("source_file")),
        metadata=dict(raw.get("metadata") or {}),
    )


def validate_plant_identity(raw: Mapping[str, Any]) -> PlantIdentity:
    """Validate the minimum tenant/plant identity required for onboarding."""
    organization_id = _text(raw.get("organization_id"))
    plant_id = _text(raw.get("plant_id"))
    name = _text(raw.get("name") or raw.get("plant_name"))
    if not organization_id or not plant_id or not name:
        raise ValueError("organization_id, plant_id and plant name are required")
    return PlantIdentity(
        organization_id=organization_id,
        plant_id=plant_id,
        name=name,
        industry=_text(raw.get("industry")),
        timezone=_text(raw.get("timezone")) or "Asia/Kolkata",
    )


def build_onboarding_package(plant: Mapping[str, Any], records: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Build a deterministic, JSON-safe package for existing ANVIQO consumers."""
    identity = validate_plant_identity(plant)
    normalized: List[OnboardingRecord] = []
    for raw in records:
        rtype = _text(raw.get("record_type") or raw.get("entity_type") or raw.get("type")) or "ASSET"
        normalized.append(normalize_record(raw, rtype))
    return {
        "contract": ONBOARDING_VERSION,
        "plant": asdict(identity),
        "records": [asdict(r) for r in normalized],
        "counts": {"records": len(normalized)},
        "safety": dict(SAFETY),
        "principle": "CHANGE DATA, NOT CODE",
        "reasoning_engine": "existing_v5_intelligence_only",
    }


__all__ = [
    "ONBOARDING_VERSION",
    "SAFETY",
    "PlantIdentity",
    "OnboardingRecord",
    "normalize_record",
    "validate_plant_identity",
    "build_onboarding_package",
]
