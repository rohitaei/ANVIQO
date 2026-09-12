"""ANVIQO Universal Industrial Onboarding V1.

Configuration/data adapter only. Converts plant-supplied engineering records
into one stable onboarding contract so existing V5 intelligence remains
unchanged. Principle: CHANGE DATA, NOT CODE.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Mapping
import re

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

def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _text(value).lower())

def _pick(raw: Mapping[str, Any], *aliases: str) -> Any:
    wanted = {_key(a) for a in aliases}
    for key, value in raw.items():
        if _key(key) in wanted and _text(value):
            return value
    return ""

def _engineering_metadata(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """Preserve common engineering-sheet fields without changing V5 semantics."""
    metadata = dict(raw.get("metadata") or {})
    aliases = {
        "io_type": ("io_type", "I/O TYPE", "IO TYPE", "signal type", "signal_type"),
        "plc_address": ("plc_address", "PLC ADDRESS", "S7 PLC ADRESS", "S7 PLC ADDRESS", "PLC ADRESS", "address"),
        "plc_tag": ("plc_tag", "PLC TAG", "PLC TAG NAME", "TAG NAME", "TAG"),
        "panel": ("panel", "PANEL", "PANEL NAME"),
        "tb": ("tb", "TB", "TB NAME", "TB NO", "TB NUMBER", "TERMINAL BLOCK"),
        "tb_no": ("tb_no", "TB NO", "TB NUMBER"),
        "jb": ("jb", "JB", "JB NAME", "JB NO", "JUNCTION BOX"),
        "jb_no": ("jb_no", "JB NO", "JB NUMBER"),
        "range": ("range", "RANGE", "instrument range", "measurement range"),
        "unit": ("unit", "UNIT", "engineering unit", "engg unit"),
        "model": ("model", "MODEL", "model no", "model number"),
        "criticality": ("criticality", "CRITICALITY", "critical"),
        "description": ("description", "DESCRIPTION", "service description", "instrument description"),
    }
    for canonical, names in aliases.items():
        value = _pick(raw, *names)
        if _text(value) and canonical not in metadata:
            metadata[canonical] = value
    # Keep additional source columns available for evidence/traceability.
    for key, value in raw.items():
        if _text(value) and _key(key) not in {"metadata", "externalid", "id", "tag", "tagname"}:
            metadata.setdefault(_text(key), value)
    return metadata

def normalize_record(raw: Mapping[str, Any], record_type: str) -> OnboardingRecord:
    """Normalize canonical and common engineering spreadsheet column names."""
    tag = _text(_pick(raw, "tag", "tag_name", "PLC TAG", "PLC TAG NAME", "TAG NAME"))
    rid = _text(_pick(raw, "external_id", "id", "asset_id", "tag", "tag_name", "PLC TAG", "PLC TAG NAME", "TAG NAME"))
    if not rid:
        raise ValueError("external_id, id, tag, PLC TAG or asset_id is required")
    return OnboardingRecord(
        record_type=_text(record_type).upper(),
        external_id=rid,
        name=_text(_pick(raw, "name", "description", "equipment_name", "instrument description", "service description")),
        area=_text(_pick(raw, "area", "unit", "location", "area name", "plant area")),
        service=_text(_pick(raw, "service", "process_service", "service description", "process")),
        asset_type=_text(_pick(raw, "asset_type", "type", "instrument_type", "equipment type", "instrument type")),
        tag=tag,
        parent_id=_text(_pick(raw, "parent_id", "parent", "equipment_id", "parent tag")),
        source=_text(_pick(raw, "source", "document", "source_file", "source document", "file name")),
        metadata=_engineering_metadata(raw),
    )

def validate_plant_identity(raw: Mapping[str, Any]) -> PlantIdentity:
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
    identity = validate_plant_identity(plant)
    normalized: List[OnboardingRecord] = []
    for raw in records:
        rtype = _text(_pick(raw, "record_type", "entity_type", "type")) or "ASSET"
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

__all__ = ["ONBOARDING_VERSION", "SAFETY", "PlantIdentity", "OnboardingRecord", "normalize_record", "validate_plant_identity", "build_onboarding_package"]
