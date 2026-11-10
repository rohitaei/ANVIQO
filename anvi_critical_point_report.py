"""Complete selected-plant critical-point report formatter.

This module formats only the snapshot supplied by the caller. It never opens a
global/demo database and never falls back to another plant.
"""
from __future__ import annotations

import json
import re
from typing import Any


def is_critical_point_request(question: Any) -> bool:
    """Recognize natural-language requests for the complete critical-point list."""
    q = " ".join(str(question or "").lower().split())
    terms = (
        "critical equipment", "which equipment is critical",
        "critical point", "critical-point", "critical points",
        "critical tags", "critical tag", "critical count",
        "unique critical", "all critical", "every critical",
        "return every unique critical", "show all critical",
    )
    return any(term in q for term in terms)


def _normalise_tag(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _metadata(point: dict[str, Any]) -> dict[str, Any]:
    meta = point.get("metadata")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    return meta if isinstance(meta, dict) else {}


def _field(point: dict[str, Any], meta: dict[str, Any], *names: str) -> str:
    wanted = {re.sub(r"[^a-z0-9]", "", n.lower()) for n in names}
    for source in (point, meta):
        for key, value in source.items():
            if re.sub(r"[^a-z0-9]", "", str(key).lower()) in wanted and value not in (None, ""):
                return str(value).strip()
    return "UNAVAILABLE"


def build_critical_point_report(snapshot: dict[str, Any] | None, plant_id: str = "", plant_name: str = "") -> dict[str, Any]:
    """Return a complete, deduplicated report from one selected-plant snapshot."""
    snap = snapshot if isinstance(snapshot, dict) else {}
    mode = str(snap.get("mode") or "ONBOARDING_DATA").upper()
    source = str(snap.get("source") or "UNAVAILABLE")
    points = snap.get("points") or snap.get("records") or []
    if not isinstance(points, list) or not points:
        answer = (
            "ANVI — Critical Point Report\n"
            f"Selected plant: {plant_name or plant_id or 'UNAVAILABLE'}.\n"
            "Critical-point data: UNAVAILABLE — no point records are onboarded in the selected plant snapshot.\n"
            "Measured value, unit, timestamp, configured limit, evidence, severity reason and human action: UNAVAILABLE.\n"
            "No other plant or global demo data was used."
        )
        return {"answer": answer, "status": "NO_DATA", "count": 0, "evidence": [],
                "plant_id": plant_id, "source": source, "mode": mode,
                "read_only": True, "plc_write": False, "scada_control": False,
                "automatic_authorization": False, "automatic_execution": False,
                "human_decision_required": True}

    critical = [
        p for p in points
        if isinstance(p, dict) and (
            str(p.get("state") or p.get("status") or "").upper() == "CRITICAL"
            or str(_metadata(p).get("criticality") or "").upper() == "HIGH"
        )
    ]
    unique: dict[str, dict[str, Any]] = {}
    duplicate_rows = 0
    for point in critical:
        meta = _metadata(point)
        tag = str(point.get("tag") or point.get("external_id") or point.get("id") or "").strip()
        key = _normalise_tag(tag)
        if not key:
            # Preserve an untagged source row without inventing an engineering tag.
            key = "UNTAGGED:" + str(point.get("id") or len(unique) + 1)
            tag = "TAG UNAVAILABLE (" + key.split(":", 1)[1] + ")"
        if key in unique:
            duplicate_rows += 1
            previous = unique[key]
            # Prefer the row with the richer evidence payload; never merge values
            # from different records into a fabricated point.
            old_meta = _metadata(previous)
            old_score = sum(v not in (None, "", {}, []) for v in previous.values()) + sum(v not in (None, "", {}, []) for v in old_meta.values())
            new_score = sum(v not in (None, "", {}, []) for v in point.values()) + sum(v not in (None, "", {}, []) for v in meta.values())
            if new_score > old_score:
                unique[key] = point
        else:
            unique[key] = point

    ordered = sorted(unique.values(), key=lambda p: str(p.get("tag") or p.get("external_id") or p.get("id") or "").upper())
    reported_critical_count = snap.get("critical_count", snap.get("critical"))
    try:
        reported_count_text = str(int(reported_critical_count)) if reported_critical_count is not None else "UNAVAILABLE"
    except (TypeError, ValueError):
        reported_count_text = "UNAVAILABLE"
    reconciliation = "UNAVAILABLE" if reported_count_text == "UNAVAILABLE" else ("MATCH" if int(reported_count_text) == len(critical) else "MISMATCH")
    lines = [
        f"ANVI — Critical Point Report ({'SIMULATION' if mode == 'SIMULATION' else mode})",
        f"Selected plant: {plant_name or plant_id or 'UNAVAILABLE'}.",
        f"Snapshot-reported critical count: {reported_count_text} | Critical source rows: {len(critical)} | Unique critical tags: {len(ordered)} | Duplicate rows collapsed: {duplicate_rows} | Count reconciliation: {reconciliation}.",
        f"Source: {source}.",
    ]
    evidence = []
    for point in ordered:
        meta = _metadata(point)
        tag = str(point.get("tag") or point.get("external_id") or point.get("id") or "TAG UNAVAILABLE").strip()
        area = str(point.get("area") or meta.get("area") or "UNAVAILABLE")
        value = _field(point, meta, "value", "measured_value", "current_value")
        unit = _field(point, meta, "unit", "engineering_unit", "engg_unit", "units")
        timestamp = _field(point, meta, "timestamp", "observed_at", "sample_time", "updated_at")
        limit = _field(point, meta, "configured_limit", "alarm_limit", "critical_limit", "high_high_limit", "low_low_limit", "HH_limit", "LL_limit")
        description = str(point.get("description") or point.get("name") or meta.get("description") or "UNAVAILABLE")
        point_state = str(point.get("state") or point.get("status") or "UNAVAILABLE").upper()
        configured_criticality = str(meta.get("criticality") or point.get("criticality") or "").upper()
        severity_reason = str(meta.get("severity_reason") or point.get("severity_reason") or (
            "Selected-plant snapshot state is CRITICAL. No validated alarm threshold/comparator was supplied; a process-limit breach cannot be confirmed."
            if point_state == "CRITICAL" else
            "Instrument is configured with HIGH criticality in the selected plant's onboarded PCI record. This is an asset classification, not proof of an active alarm; live alarm severity and process-limit breach are not established."
            if configured_criticality == "HIGH" else
            "Critical state was supplied by the selected-plant snapshot; no validated alarm threshold/comparator was supplied."
        ))
        action = str(meta.get("recommended_human_action") or meta.get("human_action") or (
            "Authorized operations/instrumentation personnel: verify signal quality, engineering units, operating mode, approved alarm limits and process trend against current plant documents; follow site SOP. Do not act on this simulation alone."
        ))
        # Selected-plant PCI is authoritative for instrument identity.
        # Simulation fixture sources (including spare inventory) are not instrument evidence.
        point_source = str(point.get("source") or meta.get("source_document") or source)
        measurement_provenance = "SIMULATION SNAPSHOT (not live telemetry)" if mode == "SIMULATION" else "UNAVAILABLE"
        lines.extend([
            f"{tag} | Area: {area} | Description: {description}",
            f"Measured value: {value} | Unit: {unit} | Timestamp: {timestamp}",
            f"Configured limit: {limit}",
            f"Instrument evidence: {point_source}; state={str(point.get('state') or point.get('status') or 'UNAVAILABLE').upper()}.",
            f"Measurement provenance: {measurement_provenance}.",
            f"Severity reason: {severity_reason}",
            f"Recommended human action: {action}",
        ])
        evidence.append({
            "tag": tag, "area": area, "description": description,
            "measured_value": value, "unit": unit, "timestamp": timestamp,
            "configured_limit": limit, "evidence": point_source,
            "measurement_provenance": measurement_provenance,
            "severity": ("CRITICAL" if point_state == "CRITICAL" else "HIGH CRITICALITY"), "severity_reason": severity_reason,
            "recommended_human_action": action,
        })

    if not ordered:
        lines.append("No point is marked CRITICAL in this selected-plant snapshot.")
    if mode == "SIMULATION":
        lines.append("Simulation only: this is not live plant telemetry and does not establish actual equipment condition.")
    lines.append("Unavailable fields are explicitly labelled UNAVAILABLE; no values or limits have been inferred.")
    lines.append("Safety: read-only; PLC WRITE BLOCKED; SCADA CONTROL BLOCKED; HUMAN DECISION REQUIRED.")
    return {"answer": "\n".join(lines), "status": "OK", "count": len(ordered),
            "source_row_count": len(critical), "snapshot_reported_critical_count": reported_count_text, "count_reconciliation": reconciliation, "duplicate_rows_collapsed": duplicate_rows,
            "evidence": evidence, "plant_id": plant_id, "source": source, "mode": mode,
            "read_only": True, "plc_write": False, "scada_control": False,
            "automatic_authorization": False, "automatic_execution": False,
            "human_decision_required": True}
