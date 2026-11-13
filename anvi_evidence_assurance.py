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

    reported_state_counts = {}
    for key in ("healthy", "warning", "critical"):
        raw_count = data.get(key)
        try:
            reported_state_counts[key] = int(raw_count) if raw_count is not None else None
        except (TypeError, ValueError):
            reported_state_counts[key] = None
    if reported_state_counts["critical"] is None and data.get("critical_count") is not None:
        try:
            reported_state_counts["critical"] = int(data.get("critical_count"))
        except (TypeError, ValueError):
            pass
    state_counts_reconciled = all(
        reported_state_counts[key.lower()] is None
        or reported_state_counts[key.lower()] == state_counts[key]
        for key in state_counts
    )

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

    # Reconcile the area roll-up with point-level evidence. Area rows in the
    # tenant adapter use name/count; older demo snapshots may use area/total.
    observed_areas: dict[str, dict[str, int]] = {}
    for point in points:
        area_name = str(point.get("area") or "GENERAL").strip().upper() or "GENERAL"
        bucket = observed_areas.setdefault(
            area_name, {"count": 0, "healthy": 0, "warning": 0, "critical": 0}
        )
        bucket["count"] += 1
        state = str(point.get("state") or point.get("status") or "").upper()
        if state in ("HEALTHY", "WARNING", "CRITICAL"):
            bucket[state.lower()] += 1

    reported_area_rows = [
        row for row in (data.get("areas") or []) if isinstance(row, dict)
    ]
    area_total_reconciled = None
    area_state_counts_reconciled = None
    if reported_area_rows:
        reported_areas = {}
        for row in reported_area_rows:
            name = str(row.get("name") or row.get("area") or "GENERAL").strip().upper()
            reported_areas[name] = row
        try:
            reported_area_total = sum(
                int(row.get("count", row.get("total", 0)) or 0)
                for row in reported_area_rows
            )
            area_total_reconciled = reported_area_total == len(points)
        except (TypeError, ValueError):
            area_total_reconciled = False

        area_state_counts_reconciled = True
        for name, observed in observed_areas.items():
            row = reported_areas.get(name)
            if row is None:
                area_state_counts_reconciled = False
                continue
            for state_key in ("healthy", "warning", "critical"):
                if state_key not in row:
                    continue
                try:
                    if int(row.get(state_key) or 0) != observed[state_key]:
                        area_state_counts_reconciled = False
                except (TypeError, ValueError):
                    area_state_counts_reconciled = False
        if any(name not in observed_areas for name in reported_areas):
            area_state_counts_reconciled = False

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
    if area_total_reconciled is False:
        findings.append("AREA_TOTAL_MISMATCH")
    if area_state_counts_reconciled is False:
        findings.append("AREA_STATE_COUNT_MISMATCH")
    if not points:
        findings.append("NO_POINT_EVIDENCE")
    if total_reported != len(points):
        findings.append("POINT_TOTAL_MISMATCH")
    if unknown_state_count:
        findings.append("UNKNOWN_OR_UNRATED_POINT_STATES")
    if not state_counts_reconciled:
        findings.append("STATE_COUNT_MISMATCH")
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
        (area_total_reconciled is not False)
        and (area_state_counts_reconciled is not False)
        and bool(points)
        and counts_reconciled
        and state_counts_reconciled
        and (mode != "SIMULATION" or unknown_state_count == 0)
        and event_count_reconciled
        and changed_count_reconciled
        and health_reconciled
        and timestamp is not None
        and fresh
    )
    assurance_status = (
        "CONSISTENT_SIMULATION_EVIDENCE" if structurally_consistent and mode == "SIMULATION"
        else "CONSISTENT_ONBOARDING_DATA" if structurally_consistent and mode in ("ONBOARDING", "ONBOARDING_DATA")
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
        "reported_state_counts": reported_state_counts,
        "state_counts_reconciled": state_counts_reconciled,
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
            "state_counts_reconciled": state_counts_reconciled,
            "event_count_reconciled": event_count_reconciled,
            "changed_count_reconciled": changed_count_reconciled,
            "health_score_reconciled": health_reconciled,
            "area_total_reconciled": area_total_reconciled,
            "area_state_counts_reconciled": area_state_counts_reconciled,
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
