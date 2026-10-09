"""ANVIQO V4.2 Industrial Connector Validation & Data Quality Operations.

Evaluates submitted observations and connector heartbeats only. It does not
open protocol sessions, connect to PLC/SCADA, or issue control commands.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from anvi_v3_5_to_v4_enterprise import SAFETY, SOURCES

POLICY_VERSION = "V4.2"
MAX_FUTURE_SKEW_SECONDS = 30


def _time(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def validate_connector_stream(
    *,
    source: dict[str, Any],
    observations: list[dict[str, Any]],
    expected_tags: list[str] | None = None,
    now: datetime | None = None,
    stale_after_seconds: int = 300,
    max_future_skew_seconds: int = MAX_FUTURE_SKEW_SECONDS,
) -> dict[str, Any]:
    """Return an evidence-based health/data-quality report for one scoped source."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("TIMEZONE_AWARE_NOW_REQUIRED")
    if stale_after_seconds < 0 or max_future_skew_seconds < 0:
        raise ValueError("TIME_THRESHOLDS_MUST_BE_NONNEGATIVE")
    if not isinstance(observations, list):
        raise ValueError("OBSERVATIONS_MUST_BE_LIST")

    source_type = str(source.get("source_type", "")).upper()
    source_id = str(source.get("source_id", "")).strip()
    configured = source_type in SOURCES and bool(source_id) and all(
        str(source.get(k, "")).strip() for k in ("organization_id", "plant_id")
    ) and source.get("read_only", True) is True
    if source_type not in SOURCES:
        connector_state = "UNSUPPORTED"
    elif source.get("read_only", True) is not True:
        connector_state = "BLOCKED_WRITE_MODE"
    elif not configured:
        connector_state = "NOT_CONFIGURED"
    elif not observations:
        connector_state = "UNAVAILABLE"
    else:
        connector_state = "PENDING_ASSESSMENT"

    now_utc = now.astimezone(timezone.utc)
    parsed_times: list[datetime] = []
    invalid_timestamps = 0
    future_timestamps = 0
    stale_timestamps = 0
    missing_values = 0
    missing_tags = 0
    seen_keys: set[tuple[str, str]] = set()
    duplicate_count = 0
    sequences_by_tag: dict[str, list[int]] = {}
    seen_payloads: set[tuple[str, str, str, str]] = set()
    valid_rows = 0
    scoped_org = str(source.get("organization_id", ""))
    scoped_plant = str(source.get("plant_id", ""))
    scope_errors = 0

    for row in observations:
        if (str(row.get("organization_id", "")) != scoped_org
                or str(row.get("plant_id", "")) != scoped_plant
                or str(row.get("source_id", "")) != source_id):
            scope_errors += 1
            continue
        tag = str(row.get("tag", "")).strip()
        if not tag:
            missing_tags += 1
        value = row.get("value")
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_values += 1
        else:
            valid_rows += 1

        timestamp = _time(row.get("observed_at") or row.get("timestamp"))
        if timestamp is None:
            invalid_timestamps += 1
        else:
            parsed_times.append(timestamp)
            age = (now_utc - timestamp).total_seconds()
            if age < -max_future_skew_seconds:
                future_timestamps += 1
            elif age > stale_after_seconds:
                stale_timestamps += 1

        sequence = row.get("sequence")
        if sequence is not None:
            try:
                seq = int(sequence)
                if str(sequence).strip() != "" and seq >= 0 and tag:
                    sequences_by_tag.setdefault(tag, []).append(seq)
            except (ValueError, TypeError, OverflowError):
                invalid_timestamps += 0  # Sequence validity is reported separately below.
        key = (tag, str(sequence)) if sequence is not None else (
            tag, str(row.get("observed_at") or row.get("timestamp") or "")
        )
        if key in seen_keys:
            duplicate_count += 1
        seen_keys.add(key)
        payload_key = (tag, str(row.get("observed_at") or row.get("timestamp") or ""),
                       str(value), str(sequence or ""))
        if payload_key in seen_payloads and key not in seen_keys:
            duplicate_count += 1
        seen_payloads.add(payload_key)

    sequence_gaps = 0
    for seqs in sequences_by_tag.values():
        ordered = sorted(set(seqs))
        if len(ordered) > 1:
            sequence_gaps += sum(max(0, b - a - 1) for a, b in zip(ordered, ordered[1:]))

    observed_tags = {str(row.get("tag", "")).strip() for row in observations if str(row.get("tag", "")).strip()}
    expected = {str(tag).strip() for tag in (expected_tags or []) if str(tag).strip()}
    missing_expected_tags = sorted(expected - observed_tags)
    total = len(observations)
    quality_issues = (invalid_timestamps + future_timestamps + stale_timestamps
                      + missing_values + missing_tags + duplicate_count + sequence_gaps
                      + len(missing_expected_tags) + scope_errors)
    if scope_errors:
        connector_state = "SCOPE_VIOLATION"
    elif source_type not in SOURCES or not configured:
        pass
    elif not observations:
        connector_state = "UNAVAILABLE"
    elif not parsed_times:
        connector_state = "DEGRADED"
    elif max((now_utc - t).total_seconds() for t in parsed_times) > stale_after_seconds:
        connector_state = "STALE" if all((now_utc - t).total_seconds() > stale_after_seconds for t in parsed_times) else "DEGRADED"
    elif quality_issues:
        connector_state = "DEGRADED"
    else:
        connector_state = "HEALTHY"

    # Last-seen only derives from valid timestamps in the submitted telemetry.
    last_seen = max(parsed_times).isoformat() if parsed_times else None
    return {
        "policy_version": POLICY_VERSION,
        "status": connector_state,
        "source_id": source_id or None,
        "source_type": source_type or None,
        "observations_received": total,
        "valid_value_rows": valid_rows,
        "last_seen": last_seen,
        "telemetry_observed_in_scope": bool(observations) and scope_errors == 0,
        "live_connection_verified": False,
        "timestamp_quality": {
            "invalid_or_timezone_missing": invalid_timestamps,
            "future_beyond_tolerance": future_timestamps,
            "stale": stale_timestamps,
            "max_future_skew_seconds": max_future_skew_seconds,
        },
        "data_quality": {
            "missing_tags": missing_tags,
            "missing_values": missing_values,
            "duplicate_observations": duplicate_count,
            "sequence_gaps": sequence_gaps,
            "expected_tags_missing": missing_expected_tags,
            "scope_violations": scope_errors,
            "quality_issue_count": quality_issues,
        },
        "sequence_ranges": {
            tag: {"first": min(values), "last": max(values), "unique_count": len(set(values))}
            for tag, values in sorted(sequences_by_tag.items()) if values
        },
        "limitations": [
            "Assessment covers only the observations submitted in this request.",
            "No protocol handshake or physical PLC/SCADA connection was initiated.",
            "A telemetry payload is not proof of a continuously healthy network connection.",
        ],
        "safety": dict(SAFETY),
    }


def register(app):
    from flask import jsonify, request, session

    @app.post("/api/v4/integration/validate-stream")
    def v42_validate_stream():
        organization_id = str(session.get("organization_id", ""))
        plant_id = str(session.get("plant_id", ""))
        if not organization_id or not plant_id:
            return jsonify({"status": "TENANT_UNAVAILABLE", "safety": dict(SAFETY)}), 409
        body = request.get_json(silent=True) or {}
        source = body.get("source", {})
        observations = body.get("observations", [])
        if not isinstance(source, dict) or not isinstance(observations, list):
            return jsonify({"status": "BAD_REQUEST", "message": "source must be an object and observations a list",
                            "safety": dict(SAFETY)}), 400
        if (str(source.get("organization_id", "")) != organization_id
                or str(source.get("plant_id", "")) != plant_id):
            return jsonify({"status": "FORBIDDEN", "message": "TENANT_OR_PLANT_BOUNDARY_VIOLATION",
                            "safety": dict(SAFETY)}), 403
        for row in observations:
            if not isinstance(row, dict):
                return jsonify({"status": "BAD_REQUEST", "message": "each observation must be an object",
                                "safety": dict(SAFETY)}), 400
            if (str(row.get("organization_id", "")) != organization_id
                    or str(row.get("plant_id", "")) != plant_id
                    or str(row.get("source_id", "")) != str(source.get("source_id", ""))):
                return jsonify({"status": "FORBIDDEN", "message": "TENANT_OR_PLANT_BOUNDARY_VIOLATION",
                                "safety": dict(SAFETY)}), 403
        try:
            report = validate_connector_stream(
                source=source,
                observations=observations,
                expected_tags=body.get("expected_tags", []),
                stale_after_seconds=int(body.get("stale_after_seconds", 300)),
                max_future_skew_seconds=int(body.get("max_future_skew_seconds", MAX_FUTURE_SKEW_SECONDS)),
            )
            return jsonify(report)
        except (ValueError, TypeError) as exc:
            return jsonify({"status": "BAD_REQUEST", "message": str(exc), "safety": dict(SAFETY)}), 400
