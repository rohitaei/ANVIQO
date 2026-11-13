"""Evidence assurance contract for ANVIQO plant intelligence.

Computes consistency and completeness from one selected-plant snapshot.
It never upgrades simulation/onboarding evidence into live telemetry and
never infers physical causation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "automatic_authorization": False,
    "automatic_execution": False,
}


def _parse_timestamp(value: Any):
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def build_evidence_assurance(
    snapshot: dict[str, Any] | None,
    *,
    plant_id: str = "",
    organization_id: str = "",
    now: datetime | None = None,
    freshness_seconds: int = 300,
) -> dict[str, Any]:
    """Return a transparent quality passport for a single plant snapshot."""
    data = snapshot if isinstance(snapshot, dict) else {}
    points = [p for p in (data.get("points") or data.get("records") or []) if isinstance(p, dict)]
    mode = str(data.get("mode") or "UNKNOWN").upper()
    source = str(data.get("source") or "UNSPECIFIED")
    total_reported = data.get("total_io", data.get("record_count", len(points)))
    try:
        total_reported = int(total_reported)
    except (TypeError, ValueError):
        total_reported = -1

    state_counts = {"HEALTHY": 0, "WARNING": 0, "CRITICAL": 0}
    unknown_state_count = 0
    event_count = 0
    changed_count = 0
    for point in points:
        state = str(point.get("state") or point.get("status") or "").upper()
        if state in state_counts:
            state_counts[state] += 1
        else:
            unknown_state_count += 1
        event_count += int(bool(point.get("event_active")))
        changed_count += int(bool(point.get("changed")))

    status_coverage = sum(state_counts.values())
    coverage_pct = round((status_coverage / len(points)) * 100, 2) if points else 0.0
    counts_reconciled = (
        total_reported >= 0
        and total_reported == len(points)
        and status_coverage + unknown_state_count == len(points)
    )
    reported_events = data.get("active_events")
    if isinstance(reported_events, list):
        reported_event_count = len(reported_events)
    else:
        try:
            reported_event_count = int(reported_events)
        except (TypeError, ValueError):
            reported_event_count = None
    event_count_reconciled = (
        reported_event_count is None or reported_event_count == event_count
    )
    reported_changed = data.get("changed")
    try:
        reported_changed = int(reported_changed) if reported_changed is not None else None
    except (TypeError, ValueError):
        reported_changed = None
    changed_count_reconciled = (
        reported_changed is None or reported_changed == changed_count
    )

    recomputed_health = None
    if points and status_coverage == len(points):
        recomputed_health = round(
            ((state_counts["HEALTHY"] + state_counts["WARNING"] * 0.5) / len(points)) * 100,
            2,
        )
    supplied_health = data.get("plant_health_score")
    try:
        supplied_health = round(float(supplied_health), 2) if supplied_health is not None else None
    except (TypeError, ValueError):
        supplied_health = None
    health_reconciled = (
        recomputed_health is None
        or supplied_health is None
        or abs(recomputed_health - supplied_health) <= 0.02
    )

    timestamp = _parse_timestamp(data.get("timestamp"))
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    age_seconds = max(0, int((clock.astimezone(timezone.utc) - timestamp).total_seconds())) if timestamp else None
    fresh = age_seconds is not None and age_seconds <= max(1, int(freshness_seconds))

    findings = []
    if not points:
        findings.append("NO_POINT_EVIDENCE")
    if total_reported != len(points):
        findings.append("POINT_TOTAL_MISMATCH")
    if unknown_state_count:
        findings.append("UNKNOWN_OR_UNRATED_POINT_STATES")
    if not event_count_reconciled:
        findings.append("ACTIVE_EVENT_COUNT_MISMATCH")
    if not changed_count_reconciled:
        findings.append("CHANGED_POINT_COUNT_MISMATCH")
    if not health_reconciled:
        findings.append("PLANT_HEALTH_SCORE_MISMATCH")
    if timestamp is None:
        findings.append("TIMESTAMP_MISSING_OR_INVALID")
    elif not fresh:
        findings.append("SNAPSHOT_STALE")
    if mode == "SIMULATION":
        findings.append("SIMULATION_NOT_LIVE_TELEMETRY")
    elif mode in ("ONBOARDING", "ONBOARDING_DATA"):
        findings.append("ONBOARDING_DATA_NOT_LIVE_TELEMETRY")
    elif mode == "UNKNOWN":
        findings.append("SOURCE_MODE_UNCONFIRMED")

    structurally_consistent = (
        bool(points)
        and counts_reconciled
        and event_count_reconciled
        and changed_count_reconciled
        and health_reconciled
        and timestamp is not None
        and fresh
    )
    assurance_status = (
        "CONSISTENT_SIMULATION_EVIDENCE" if structurally_consistent and mode == "SIMULATION"
        else "CONSISTENT_ONBOARDING_EVIDENCE" if structurally_consistent and mode in ("ONBOARDING", "ONBOARDING_DATA")
        else "PARTIAL_OR_INCONSISTENT_EVIDENCE"
    )
    canonical = {
        "plant_id": str(plant_id or data.get("plant_id") or ""),
        "organization_id": str(organization_id or data.get("organization_id") or ""),
        "timestamp": str(data.get("timestamp") or ""),
        "mode": mode,
        "source": source,
        "total_points": len(points),
        "counts": state_counts,
        "event_count": event_count,
        "changed_count": changed_count,
    }
    snapshot_id = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16].upper()

    return {
        "product": "ANVIQO",
        "capability": "PLANT_TRUTH_EVIDENCE_ASSURANCE",
        "assurance_status": assurance_status,
        "snapshot_id": snapshot_id,
        "plant_id": canonical["plant_id"],
        "organization_id": canonical["organization_id"],
        "timestamp": canonical["timestamp"],
        "age_seconds": age_seconds,
        "mode": mode,
        "source": source,
        "reported_total_points": total_reported,
        "observed_total_points": len(points),
        "state_counts": state_counts,
        "unknown_state_points": unknown_state_count,
        "state_coverage_pct": coverage_pct,
        "reported_active_events": reported_event_count,
        "observed_active_events": event_count,
        "reported_changed_points": reported_changed,
        "observed_changed_points": changed_count,
        "reported_health_score": supplied_health,
        "recomputed_health_score": recomputed_health,
        "checks": {
            "point_total_reconciled": counts_reconciled,
            "event_count_reconciled": event_count_reconciled,
            "changed_count_reconciled": changed_count_reconciled,
            "health_score_reconciled": health_reconciled,
            "timestamp_valid": timestamp is not None,
            "snapshot_fresh": fresh,
            "single_snapshot_basis": True,
        },
        "findings": findings,
        "interpretation": (
            "Snapshot counters are internally consistent. This confirms data consistency only; "
            "it does not prove physical plant condition or causation."
            if structurally_consistent else
            "Evidence is incomplete, stale or internally inconsistent. ANVI must disclose the limitation "
            "and must not present a single definitive plant-health conclusion."
        ),
        "safety": dict(SAFETY),
        **SAFETY,
    }
