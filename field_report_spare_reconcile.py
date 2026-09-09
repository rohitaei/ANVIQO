"""Authorized reconciliation for historical technician field-report spare usage.

This module repairs reports that were stored before the automatic field-report
inventory hook was deployed. It is intentionally separate from frozen V5
intelligence and only changes the authoritative critical-spare Excel inventory
through the existing idempotent sync function.
"""
from __future__ import annotations


def reconcile_field_report_spares(tag: str = "", report_id: str = "", limit: int = 1000) -> dict:
    """Apply unapplied explicit spare usage from stored technician reports.

    Safety properties:
    - Only source == technician field report is considered.
    - Only explicit used/consumed/removed language is eligible.
    - Existing APPLIED ledger entries are never applied twice.
    - No PLC or SCADA write is performed.
    """
    import plant_memory
    from field_report_runtime import extract_spare_usage, sync_field_report_spare

    wanted_tag = str(tag or "").strip().upper().replace("_", "-").replace(" ", "-")
    wanted_report = str(report_id or "").strip()
    limit = max(1, min(int(limit), 10000))

    records = plant_memory.search_all_memory(
        query="",
        tag=wanted_tag,
        limit=limit,
    )

    scanned = 0
    eligible = 0
    applied = []
    already_applied = []
    errors = []

    for report in records:
        if not isinstance(report, dict):
            continue
        if report.get("source") != "technician field report":
            continue

        rid = str(report.get("memory_id", "")).strip()
        if not rid:
            continue
        if wanted_report and rid != wanted_report:
            continue

        scanned += 1
        parsed = dict(report)
        parsed["raw_report"] = " ".join(
            str(report.get(key, "") or "")
            for key in ("event", "observation", "finding", "maintenance_action", "outcome", "spare_used", "notes")
        ).strip()
        usage = extract_spare_usage(parsed)
        if not usage:
            continue

        eligible += 1
        try:
            result = sync_field_report_spare(parsed, rid)
            if result.get("status") == "APPLIED":
                applied.append(result)
            elif result.get("status") == "ALREADY_APPLIED":
                already_applied.append(result)
            else:
                errors.append({"report_id": rid, "status": result.get("status"), "message": result.get("message", "")})
        except Exception as exc:
            errors.append({"report_id": rid, "message": str(exc)})

    return {
        "status": "OK" if not errors else "PARTIAL",
        "scanned": scanned,
        "eligible": eligible,
        "applied_count": len(applied),
        "already_applied_count": len(already_applied),
        "error_count": len(errors),
        "applied": applied,
        "already_applied": already_applied,
        "errors": errors,
        "read_only": False,
        "plc_write": False,
        "scada_control": False,
        "human_decision_required": True,
    }
