"""ANVIQO Failure Prediction synthetic telemetry loader.

This loader is deliberately isolated from production observation history.
It accepts only explicitly marked SIMULATION demo CSV data and returns an
in-memory dataset for demonstration/testing. It never calls the production
observation-history writer and never writes PLC/SCADA.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

VERSION = "ANVIQO-FP-DEMO-LOADER-V1.0"
REQUIRED_COLUMNS = {
    "timestamp",
    "tag",
    "value",
    "unit",
    "quality",
    "source_type",
    "provenance",
}

SAFETY = {
    "mode": "DEMO_SIMULATION_ONLY",
    "writes_production_history": False,
    "plc_write": False,
    "scada_control": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def _validate_timestamp(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("timestamp is required")
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {text}") from exc
    return text


def load_demo_telemetry(path: str | Path) -> Dict[str, Any]:
    """Load explicitly synthetic telemetry without touching production history."""
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(str(csv_path))

    rows: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"missing required columns: {sorted(missing)}")

        for line_number, raw in enumerate(reader, start=2):
            source_type = str(raw.get("source_type") or "").strip().upper()
            provenance = str(raw.get("provenance") or "").strip()
            if source_type != "SIMULATION" or "SIMULATION" not in provenance.upper():
                raise ValueError(
                    f"line {line_number}: demo loader requires source_type=SIMULATION "
                    "and simulation provenance"
                )
            tag = str(raw.get("tag") or "").strip().upper()
            if not tag:
                raise ValueError(f"line {line_number}: tag is required")
            timestamp = _validate_timestamp(raw.get("timestamp", ""))
            try:
                value = float(raw.get("value"))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"line {line_number}: value must be numeric") from exc
            rows.append(
                {
                    "timestamp": timestamp,
                    "tag": tag,
                    "value": value,
                    "unit": str(raw.get("unit") or "").strip(),
                    "quality": str(raw.get("quality") or "").strip().upper(),
                    "source_type": "SIMULATION",
                    "provenance": provenance,
                }
            )

    return {
        "loader_version": VERSION,
        "status": "DEMO_DATA_LOADED",
        "simulation": True,
        "production_history_write": False,
        "rows_loaded": len(rows),
        "observations": rows,
        "safety": dict(SAFETY),
    }


def summarize_demo_trend(observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize a demo-only numeric trend; no failure probability/date is inferred."""
    if len(observations) < 2:
        return {
            "status": "INSUFFICIENT_DEMO_DATA",
            "observations_used": len(observations),
            "direction": None,
        }
    ordered = sorted(observations, key=lambda row: str(row.get("timestamp") or ""))
    first, last = ordered[0], ordered[-1]
    delta = float(last["value"]) - float(first["value"])
    direction = "RISING" if delta > 0 else "FALLING" if delta < 0 else "STABLE"
    return {
        "status": "DEMO_TREND_AVAILABLE",
        "observations_used": len(ordered),
        "first": first,
        "last": last,
        "delta": delta,
        "direction": direction,
        "prediction": (
            "Conditional demonstration only: the observed numeric direction could continue "
            "if the synthetic trend persists. This is not a real plant prediction."
        ),
        "failure_probability": None,
        "failure_date": None,
        "simulation": True,
    }
