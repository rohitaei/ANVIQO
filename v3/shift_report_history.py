"""Tenant-safe bridge from historical shift-report text to predictive evidence.

This module only normalizes/persists supplied historical IndustrialPoints and
reuses the canonical V3 evidence validator. It never predicts or controls.
"""
from __future__ import annotations

from typing import Any

from v2.shift_report_adapter import parse_shift_report_text
from v3.predictive_evidence import validate_prediction_evidence


def persist_shift_report_history(
    plant_id: str,
    organization_id: str,
    report_text: str,
    *,
    source: str = "TATA METALIKS SHIFT MATERIAL REPORT",
    provenance: str = "caller-supplied historical shift report",
) -> dict[str, Any]:
    """Persist every parsed numeric point through the existing tenant boundary."""
    plant_id = str(plant_id or "").strip()
    organization_id = str(organization_id or "").strip()
    if not plant_id or not organization_id:
        raise ValueError("plant_id and organization_id are required")
    if not str(report_text or "").strip():
        raise ValueError("shift report text is required")

    from failure_prediction_history import record_tenant_industrial_point

    points = list(
        parse_shift_report_text(
            report_text,
            plant_id=plant_id,
            source=source,
        )
    )
    persisted: list[dict[str, Any]] = []
    for point in points:
        persisted.append(
            record_tenant_industrial_point(
                plant_id=plant_id,
                organization_id=organization_id,
                point=point,
                source_type="HISTORICAL_ARCHIVE",
                provenance=provenance,
            )
        )

    return {
        "plant_id": plant_id,
        "organization_id": organization_id,
        "source": source,
        "points_parsed": len(points),
        "points_persisted": len(persisted),
        "observations": persisted,
        "safety": {
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "automatic_action": False,
            "human_decision_required": True,
        },
    }


def validate_shift_report_tag_evidence(
    plant_id: str,
    tag: str,
    observations: list[dict[str, Any]],
    *,
    window_start: str | None = None,
    window_end: str | None = None,
) -> dict[str, Any]:
    """Run supplied persisted observations through the canonical V3 evidence gate."""
    return validate_prediction_evidence(
        plant_id,
        tag,
        observations,
        window_start=window_start,
        window_end=window_end,
    )


__all__ = ["persist_shift_report_history", "validate_shift_report_tag_evidence"]
