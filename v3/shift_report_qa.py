"""Tenant-safe historical shift-report Q&A bridge for ANVIQO.

This module retrieves already-persisted historical IndustrialPoint observations
through the existing tenant-scoped history boundary. It does not calculate a
trend, prediction, diagnosis, threshold, or control action.
"""
from __future__ import annotations

import re
from typing import Any, Callable

_TAG_RE = re.compile(r"\b([A-Z]{1,10}[-_ ]?\d{1,6})\b", re.I)

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


def _normalise_tag(value: str) -> str:
    value = str(value or "").strip().upper()
    return re.sub(r"[-_ ]+", "-", value)


def _extract_tag(question: str) -> str:
    match = _TAG_RE.search(str(question or ""))
    return _normalise_tag(match.group(1)) if match else ""


def is_shift_history_question(question: str) -> bool:
    low = str(question or "").strip().lower()
    if not low:
        return False
    historical = any(token in low for token in (
        "shift report", "shift report", "historical", "history",
        "hourly", "hour by hour", "previous shift", "last shift",
        "on 23/09/2026", "on 09/23/2026",
    ))
    value_request = any(token in low for token in (
        "value", "values", "reading", "readings", "observation",
        "observations", "recorded", "what was",
    ))
    return historical and value_request


def answer_shift_history_question(
    question: str,
    *,
    plant_id: str,
    organization_id: str,
    history_provider: Callable[..., list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Answer a historical-value question from the exact tenant history."""
    plant_id = str(plant_id or "").strip()
    organization_id = str(organization_id or "").strip()
    tag = _extract_tag(question)

    if not plant_id or not organization_id or not tag:
        return None
    if not is_shift_history_question(question):
        return None

    rows = history_provider(
        plant_id=plant_id,
        organization_id=organization_id,
        tag=tag,
    )
    if not isinstance(rows, list):
        raise ValueError("tenant history provider must return a list")

    safe_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("tenant history row must be a dictionary")
        if str(row.get("plant_id") or "") != plant_id:
            raise ValueError("cross-plant historical evidence is blocked")
        if str(row.get("organization_id") or "") != organization_id:
            raise ValueError("cross-organization historical evidence is blocked")
        if _normalise_tag(row.get("tag")) != tag:
            raise ValueError("historical evidence tag mismatch")
        safe_rows.append(dict(row))

    safe_rows.sort(key=lambda row: str(row.get("timestamp") or ""))

    if not safe_rows:
        return {
            "answer": f"No tenant-scoped historical shift-report observations were found for {tag}.",
            "status": "NO_DATA",
            "domain": "historical_shift_report",
            "plant_id": plant_id,
            "organization_id": organization_id,
            "tag": tag,
            "observations": [],
            "source": "tenant_scoped_history",
            "safety": dict(SAFETY),
            **SAFETY,
        }

    lines = []
    for row in safe_rows:
        timestamp = row.get("timestamp") or "timestamp unavailable"
        value = row.get("value")
        unit = str(row.get("unit") or "").strip()
        source = row.get("source") or "historical archive"
        provenance = row.get("provenance") or "not stated"
        suffix = f" {unit}" if unit else ""
        lines.append(
            f"{timestamp}: {value}{suffix} "
            f"(source: {source}; provenance: {provenance})"
        )

    return {
        "answer": (
            f"Historical shift-report evidence for {tag}: "
            + " | ".join(lines)
        ),
        "status": "OK",
        "domain": "historical_shift_report",
        "plant_id": plant_id,
        "organization_id": organization_id,
        "tag": tag,
        "observation_count": len(safe_rows),
        "observations": safe_rows,
        "source": "tenant_scoped_history",
        "evidence_type": "HISTORICAL_ARCHIVE",
        "interpretation": "Reported historical observations only; no trend or prediction was calculated.",
        "safety": dict(SAFETY),
        **SAFETY,
    }


__all__ = ["SAFETY", "is_shift_history_question", "answer_shift_history_question"]
