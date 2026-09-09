"""Persistent, provenance-aware observations for ANVIQO Failure Prediction V1.1.

This module stores observations that are actually supplied by a plant data source.
It deliberately does not sample the demo simulator and does not manufacture history.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
HISTORY_DIR = ROOT / "database" / "failure_prediction"
HISTORY_FILE = HISTORY_DIR / "observation_history.json"
VERSION = "ANVIQO-FP-HISTORY-V1.0"

_ALLOWED_SOURCE_TYPES = {
    "LIVE_TELEMETRY",
    "SCADA_READ_ONLY",
    "PLC_READ_ONLY",
    "HISTORICAL_ARCHIVE",
    "VERIFIED_FIELD_REPORT",
}

_TAG_RE = re.compile(r"^([A-Z]+)-?(\d{1,5})$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_tag(tag: str) -> str:
    value = str(tag or "").upper().strip()
    value = re.sub(r"[-_ ]+", "-", value)
    match = _TAG_RE.match(value)
    if not match:
        return re.sub(r"[^A-Z0-9]", "", value)
    return f"{match.group(1)}-{match.group(2)}"


def _load() -> Dict[str, Any]:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        data = {"version": VERSION, "observations": []}
        HISTORY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("observations"), list):
        raise RuntimeError("Invalid Failure Prediction observation history")
    return data


def _save(data: Dict[str, Any]) -> None:
    tmp = HISTORY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(HISTORY_FILE)


def record_observation(
    tag: str,
    value: float,
    timestamp: Optional[str] = None,
    source_type: str = "",
    source: str = "",
    unit: str = "",
    state: str = "",
    area: str = "",
    provenance: str = "",
) -> Dict[str, Any]:
    """Persist one externally supplied numeric observation.

    The caller must identify a non-simulation source. Duplicate tag+timestamp
    observations are idempotent and return the existing record.
    """
    normalized_tag = _norm_tag(tag)
    if not normalized_tag:
        raise ValueError("valid equipment tag is required")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        raise ValueError("numeric observation value is required")
    source_type = str(source_type or "").strip().upper()
    if source_type not in _ALLOWED_SOURCE_TYPES:
        raise ValueError("source_type must be a supported non-simulation plant source")
    source = str(source or "").strip()
    provenance = str(provenance or "").strip()
    if not source or not provenance:
        raise ValueError("source and provenance are required")
    if "SIMULATION" in source_type or "SIMULATION" in source.upper() or "DEMO" in source.upper():
        raise ValueError("simulation/demo observations are not eligible for Failure Prediction history")

    ts = str(timestamp or _now()).strip()
    try:
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("timestamp must be ISO-8601")

    data = _load()
    for existing in data["observations"]:
        if existing.get("tag") == normalized_tag and existing.get("timestamp") == ts and existing.get("source") == source:
            return existing

    record = {
        "observation_id": "FPO-" + uuid.uuid4().hex[:12].upper(),
        "tag": normalized_tag,
        "value": numeric,
        "timestamp": ts,
        "source_type": source_type,
        "source": source,
        "unit": str(unit or "").strip(),
        "state": str(state or "").strip().upper(),
        "area": str(area or "").strip(),
        "provenance": provenance,
        "simulation": False,
        "recorded_at": _now(),
    }
    data["observations"].append(record)
    data["observations"].sort(key=lambda row: (str(row.get("tag", "")), str(row.get("timestamp", ""))))
    _save(data)
    return record


def get_observations(tag: str, limit: int = 500) -> List[Dict[str, Any]]:
    normalized_tag = _norm_tag(tag)
    data = _load()
    rows = [
        row for row in data["observations"]
        if isinstance(row, dict) and row.get("tag") == normalized_tag and row.get("simulation") is False
    ]
    rows.sort(key=lambda row: str(row.get("timestamp") or ""))
    return rows[-max(1, int(limit)) :]


def history_summary(tag: str) -> Dict[str, Any]:
    rows = get_observations(tag)
    return {
        "version": VERSION,
        "tag": _norm_tag(tag),
        "count": len(rows),
        "first_timestamp": rows[0].get("timestamp") if rows else None,
        "last_timestamp": rows[-1].get("timestamp") if rows else None,
        "sources": sorted({str(row.get("source") or "") for row in rows if row.get("source")}),
        "observations": rows,
    }
