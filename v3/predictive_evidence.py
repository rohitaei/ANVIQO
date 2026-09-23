"""Universal predictive evidence quality and window validation.

This module validates supplied predictive observations before any existing
predictor is considered. It performs data-quality checks only; it does not
calculate trends, failure probability, RUL, diagnosis, or control actions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def validate_prediction_evidence(
    plant_id: str,
    tag: str,
    observations: list[dict[str, Any]],
    *,
    window_start: str | None = None,
    window_end: str | None = None,
) -> dict[str, Any]:
    """Validate tenant, tag, timestamp and numeric-value integrity.

    No observation is repaired or invented. Invalid rows are reported and
    excluded from the usable evidence list.
    """
    plant_id = str(plant_id or "").strip()
    tag = str(tag or "").strip()
    if not plant_id or not tag:
        raise ValueError("plant_id and tag are required")
    if not isinstance(observations, list):
        raise TypeError("observations must be a list")

    requested_start = _parse_timestamp(window_start)
    requested_end = _parse_timestamp(window_end)
    if window_start is not None and requested_start is None:
        raise ValueError("window_start is invalid")
    if window_end is not None and requested_end is None:
        raise ValueError("window_end is invalid")
    if requested_start is not None and requested_end is not None and requested_start > requested_end:
        raise ValueError("window_start must not be after window_end")

    usable: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    timestamps: list[datetime] = []

    for index, row in enumerate(observations):
        if not isinstance(row, dict):
            invalid_rows.append({"index": index, "reason": "observation is not a dict"})
            continue

        row_plant = row.get("plant_id")
        if row_plant is not None and str(row_plant) != plant_id:
            raise ValueError("cross-plant predictive evidence is not allowed")

        row_tag = row.get("tag")
        if row_tag is not None and str(row_tag) != tag:
            raise ValueError("predictive evidence tag mismatch")

        timestamp = _parse_timestamp(row.get("timestamp"))
        if timestamp is None:
            invalid_rows.append({"index": index, "reason": "timestamp is missing or invalid"})
            continue

        if not _is_numeric(row.get("value")):
            invalid_rows.append({"index": index, "reason": "value is not numeric"})
            continue

        if requested_start is not None and timestamp < requested_start:
            invalid_rows.append({"index": index, "reason": "timestamp is before requested window"})
            continue
        if requested_end is not None and timestamp > requested_end:
            invalid_rows.append({"index": index, "reason": "timestamp is after requested window"})
            continue

        usable.append(row)
        timestamps.append(timestamp)

    if not usable:
        quality = "EMPTY"
    elif invalid_rows:
        quality = "PARTIAL"
    else:
        quality = "VALID"

    start = min(timestamps).isoformat().replace("+00:00", "Z") if timestamps else None
    end = max(timestamps).isoformat().replace("+00:00", "Z") if timestamps else None
    span_seconds = (
        (max(timestamps) - min(timestamps)).total_seconds()
        if timestamps
        else None
    )

    return {
        "plant_id": plant_id,
        "tag": tag,
        "quality": quality,
        "usable_observation_count": len(usable),
        "invalid_observation_count": len(invalid_rows),
        "invalid_observations": invalid_rows,
        "timestamp_start": start,
        "timestamp_end": end,
        "span_seconds": span_seconds,
        "window_start": requested_start.isoformat().replace("+00:00", "Z") if requested_start else start,
        "window_end": requested_end.isoformat().replace("+00:00", "Z") if requested_end else end,
        "window_status": "VALID" if usable and not invalid_rows else ("PARTIAL" if usable else "EMPTY"),
        "evidence": list(usable),
        "safety": dict(SAFETY),
    }
