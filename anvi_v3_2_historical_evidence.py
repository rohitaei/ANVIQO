"""V3.2 historical evidence and prediction-readiness primitives.

Deterministic, tenant-neutral analytics over normalized telemetry. This module
does not predict plant outcomes by itself; it measures whether the available
history is sufficient, describes observed trend direction, and exposes the
evidence needed for human review.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import sqrt
from typing import Iterable

from anvi_v2_realtime_store import TelemetryPoint

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
    "causation_claim": False,
}

def _numeric(rows: Iterable[TelemetryPoint]) -> list[TelemetryPoint]:
    return [p for p in rows if isinstance(p.value, (int, float)) and not isinstance(p.value, bool)]

def historical_assessment(
    rows: Iterable[TelemetryPoint],
    *,
    min_samples: int = 5,
    min_span_seconds: int = 300,
) -> dict:
    ordered = sorted(_numeric(rows), key=lambda p: p.timestamp)
    if not ordered:
        return {
            "status": "NO_EVIDENCE",
            "sample_count": 0,
            "history_sufficient": False,
            "reason": "No numeric observations are available.",
            "safety": dict(SAFETY),
        }

    values = [float(p.value) for p in ordered]
    first_ts = ordered[0].timestamp.astimezone(timezone.utc)
    last_ts = ordered[-1].timestamp.astimezone(timezone.utc)
    span = max(0.0, (last_ts - first_ts).total_seconds())
    sufficient = len(values) >= min_samples and span >= min_span_seconds

    if len(values) >= 2:
        x0 = first_ts.timestamp()
        xs = [p.timestamp.astimezone(timezone.utc).timestamp() - x0 for p in ordered]
        xm = sum(xs) / len(xs)
        ym = sum(values) / len(values)
        denom = sum((x - xm) ** 2 for x in xs)
        slope_per_second = sum((x - xm) * (y - ym) for x, y in zip(xs, values)) / denom if denom else 0.0
        slope_per_hour = slope_per_second * 3600.0
        direction = "INCREASING" if slope_per_hour > 0 else ("DECREASING" if slope_per_hour < 0 else "STABLE")
        residuals = [y - (ym + slope_per_second * (x - xm)) for x, y in zip(xs, values)]
        rmse = sqrt(sum(r * r for r in residuals) / len(residuals))
    else:
        slope_per_hour = 0.0
        direction = "INSUFFICIENT"
        rmse = 0.0

    return {
        "status": "OK",
        "sample_count": len(values),
        "history_span_seconds": span,
        "history_sufficient": sufficient,
        "direction": direction,
        "first_value": values[0],
        "latest_value": values[-1],
        "minimum": min(values),
        "maximum": max(values),
        "slope_per_hour": slope_per_hour,
        "trend_rmse": rmse,
        "prediction_readiness": "READY_FOR_VALIDATION" if sufficient else "INSUFFICIENT_HISTORY",
        "reason": (
            "History meets minimum sample and time-span requirements."
            if sufficient else
            "Do not make a predictive claim: more historical evidence is required."
        ),
        "evidence_timestamps": {
            "first": first_ts.isoformat(),
            "latest": last_ts.isoformat(),
        },
        "safety": dict(SAFETY),
    }
