"""ANVIQO Universal Approved Data Ingestion V1.

Adapter boundary only: JSON/CSV inputs are converted into the existing
ANVIQO-ONBOARDING-V1 contract. No plant control, no second reasoning engine.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping

from universal_onboarding import SAFETY, build_onboarding_package

INGESTION_VERSION = "ANVIQO-INGESTION-V1"
APPROVED_FORMATS = {".json", ".csv"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        plant = data.get("plant") or data.get("plant_identity") or {}
        records = data.get("records") or data.get("data") or []
    elif isinstance(data, list):
        plant, records = {}, data
    else:
        raise ValueError("JSON root must be an object or array")
    if not isinstance(plant, Mapping) or not isinstance(records, list):
        raise ValueError("JSON plant must be an object and records must be an array")
    return plant, [r for r in records if isinstance(r, Mapping)]


def _read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {}, [{str(k): v for k, v in row.items()} for row in csv.DictReader(f)]


READERS: Dict[str, Callable] = {".json": _read_json, ".csv": _read_csv}


def ingest_file(path: str | Path, plant: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Ingest an approved file and return the standard onboarding package."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix not in APPROVED_FORMATS:
        raise ValueError(f"Unsupported source format: {source.suffix or 'none'}")
    if not source.is_file():
        raise FileNotFoundError(str(source))
    embedded_plant, records = READERS[suffix](source)
    identity = dict(plant or embedded_plant)
    if not identity:
        raise ValueError("plant identity is required for ingestion")
    fingerprint = _sha256(source)
    enriched = []
    for record in records:
        row = dict(record)
        row.setdefault("source", source.name)
        metadata = row.get("metadata")
        metadata = dict(metadata) if isinstance(metadata, dict) else {}
        metadata.setdefault("ingestion_source", source.name)
        metadata.setdefault("ingestion_sha256", fingerprint)
        row["metadata"] = metadata
        enriched.append(row)
    package = build_onboarding_package(identity, enriched)
    package["ingestion"] = {
        "version": INGESTION_VERSION,
        "source_file": source.name,
        "source_sha256": fingerprint,
        "format": suffix.lstrip("."),
        "approved_connector": True,
    }
    package["safety"] = dict(SAFETY)
    return package


def ingest_records(plant: Mapping[str, Any], records: Iterable[Mapping[str, Any]], source: str = "configured_source") -> Dict[str, Any]:
    """Connector-neutral entry point for future vendor/API adapters."""
    rows = []
    for record in records:
        row = dict(record)
        row.setdefault("source", source)
        rows.append(row)
    package = build_onboarding_package(plant, rows)
    package["ingestion"] = {"version": INGESTION_VERSION, "source": source, "approved_connector": True}
    return package


def connector_contract() -> Dict[str, Any]:
    return {
        "version": INGESTION_VERSION,
        "approved_formats": sorted(APPROVED_FORMATS),
        "contract": "ANVIQO-ONBOARDING-V1",
        "principle": "CHANGE DATA, NOT CODE",
        "safety": dict(SAFETY),
        "approved_connector": True,
        "control_operations": False,
        "reasoning_engine": "existing_v5_intelligence_only",
    }


__all__ = ["INGESTION_VERSION", "APPROVED_FORMATS", "ingest_file", "ingest_records", "connector_contract"]
