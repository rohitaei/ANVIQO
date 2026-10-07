"""ANVIQO V3.1 real-time evidence intelligence contract.

Adds deterministic data-trust primitives above the V2 telemetry contract:
freshness/staleness, missing-observation detection, duplicate detection,
observation lineage, and evidence-chain construction. This module is
simulation/edge-contract only and never writes to PLC/SCADA.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Iterable

from anvi_v2_realtime_store import TelemetryPoint, StreamEvent

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
    "causation_claim": False,
}

@dataclass(frozen=True)
class ObservationTrust:
    tag: str
    observation_count: int
    latest_timestamp: str | None
    age_seconds: float | None
    stale: bool
    missing: bool
    bad_quality_count: int
    duplicate_count: int
    evidence_strength: str

def _utc_now(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return value.astimezone(timezone.utc)

def observation_fingerprint(point: TelemetryPoint) -> str:
    raw = "|".join([
        point.organization_id, point.plant_id, point.tag,
        point.timestamp.astimezone(timezone.utc).isoformat(),
        str(point.value), point.engineering_unit,
        point.quality.upper(), point.source,
    ])
    return sha256(raw.encode("utf-8")).hexdigest()

def assess_observations(
    points: Iterable[TelemetryPoint],
    *,
    expected_tags: Iterable[str] = (),
    now: datetime | None = None,
    stale_after_seconds: int = 300,
) -> dict:
    rows = list(points)
    current = _utc_now(now)
    by_tag: dict[str, list[TelemetryPoint]] = {}
    for point in rows:
        by_tag.setdefault(point.tag, []).append(point)

    expected = {str(t) for t in expected_tags if str(t)}
    tags = expected | set(by_tag)
    observations: list[ObservationTrust] = []
    for tag in sorted(tags):
        tag_rows = sorted(by_tag.get(tag, []), key=lambda p: p.timestamp)
        latest = tag_rows[-1] if tag_rows else None
        age = None if latest is None else max(0.0, (current - latest.timestamp.astimezone(timezone.utc)).total_seconds())
        fingerprints = [observation_fingerprint(p) for p in tag_rows]
        duplicate_count = len(fingerprints) - len(set(fingerprints))
        bad = sum(p.quality.upper() in {"BAD", "UNCERTAIN"} for p in tag_rows)
        stale = latest is not None and age > stale_after_seconds
        missing = latest is None
        if missing:
            strength = "NO_EVIDENCE"
        elif bad or stale or duplicate_count:
            strength = "WEAK"
        else:
            strength = "STRONG"
        observations.append(ObservationTrust(
            tag=tag,
            observation_count=len(tag_rows),
            latest_timestamp=None if latest is None else latest.timestamp.astimezone(timezone.utc).isoformat(),
            age_seconds=age,
            stale=stale,
            missing=missing,
            bad_quality_count=bad,
            duplicate_count=duplicate_count,
            evidence_strength=strength,
        ))

    stale_tags = [x.tag for x in observations if x.stale]
    missing_tags = [x.tag for x in observations if x.missing]
    weak_tags = [x.tag for x in observations if x.evidence_strength == "WEAK"]
    return {
        "status": "OK",
        "observation_count": len(rows),
        "tag_count": len(observations),
        "stale_count": len(stale_tags),
        "missing_count": len(missing_tags),
        "weak_evidence_count": len(weak_tags),
        "stale_tags": stale_tags,
        "missing_tags": missing_tags,
        "weak_evidence_tags": weak_tags,
        "observations": [x.__dict__ for x in observations],
        "evidence_rule": "fresh + good quality + non-duplicate observations are stronger evidence",
        "safety": dict(SAFETY),
    }

def build_evidence_chain(
    points: Iterable[TelemetryPoint],
    events: Iterable[StreamEvent],
    *,
    tag: str | None = None,
    window_seconds: int = 300,
) -> dict:
    telemetry = [p for p in points if tag is None or p.tag == tag]
    stream = list(events)
    links = []
    for event in stream:
        for point in telemetry:
            delta = abs((event.timestamp.astimezone(timezone.utc) - point.timestamp.astimezone(timezone.utc)).total_seconds())
            if delta <= window_seconds:
                links.append({
                    "observation_id": point.observation_id,
                    "event_id": event.event_id,
                    "relationship": "temporally_associated",
                    "delta_seconds": delta,
                    "causal_claimed": False,
                })
    return {
        "status": "OK",
        "nodes": {
            "observations": len(telemetry),
            "events": len(stream),
        },
        "links": links,
        "lineage": [
            "edge_observation",
            "quality_check",
            "freshness_check",
            "event_association",
            "operator_review",
        ],
        "causal_claimed": False,
        "safety": dict(SAFETY),
    }
