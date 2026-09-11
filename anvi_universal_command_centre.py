"""ANVIQO universal Command Centre data adapter.

Keeps frozen V5 intelligence and the existing demo simulator intact while
routing the Command Centre data surface to the currently selected tenant
plant when that plant has onboarded data.

Principle: CHANGE DATA, NOT CODE.
Safety: read-only; no PLC/SCADA writes; no automatic execution.
"""
from __future__ import annotations

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


def _active_plant() -> str:
    try:
        from flask import has_request_context, session
        if has_request_context():
            return str(session.get("plant_id") or "").strip()
    except Exception:
        pass
    return ""


def _tenant_snapshot(plant_id: str) -> dict[str, Any] | None:
    """Build a dashboard-compatible snapshot from tenant-scoped knowledge.

    Return None when the selected plant has no indexed data so callers can
    retain the legacy primary-plant demo behaviour rather than fabricating
    live values.
    """
    if not plant_id:
        return None
    try:
        import anvi_plant_ingestion_runtime as ingestion
        import anvi_tenant_store as store
        ingestion.init_schema()
        p = store._placeholder()
        with store._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content "
                f"FROM anviqo_plant_knowledge WHERE plant_id={p} ORDER BY created_at DESC",
                (plant_id,),
            )
            rows = cur.fetchall()
    except Exception:
        return None

    if not rows:
        return None

    points: list[dict[str, Any]] = []
    areas: dict[str, dict[str, Any]] = {}
    for row in rows:
        record_type, external_id, name, area, service, asset_type, tag, parent_id, source, metadata, content = row
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        metadata = metadata if isinstance(metadata, dict) else {}
        point = {
            "id": str(external_id or ""),
            "tag": str(tag or ""),
            "name": str(name or ""),
            "area": str(area or ""),
            "service": str(service or ""),
            "asset_type": str(asset_type or ""),
            "parent_id": str(parent_id or ""),
            "record_type": str(record_type or ""),
            "source": str(source or ""),
            "status": "ONBOARDED_DATA",
            "state": "ONBOARDED_DATA",
            "mode": "ONBOARDING",
            "metadata": metadata,
        }
        points.append(point)
        area_name = str(area or "GENERAL") or "GENERAL"
        bucket = areas.setdefault(area_name, {"name": area_name, "count": 0, "healthy": 0, "warning": 0, "critical": 0})
        bucket["count"] += 1

    area_list = list(areas.values())
    return {
        "status": "OK",
        "mode": "ONBOARDING_DATA",
        "source": "ANVIQO TENANT PLANT KNOWLEDGE",
        "total_io": len(points),
        "healthy": 0,
        "warning": 0,
        "critical": 0,
        "critical_count": 0,
        "changed": 0,
        "active_events": [],
        "plant_health_score": None,
        "health_status": "DATA_ONLY",
        "area_count": len(area_list),
        "areas": area_list,
        "points": points,
        "records": points,
        "plant_id": plant_id,
        "safety": dict(SAFETY),
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
    }


def get_live_pci_snapshot(original_getter):
    """Compatibility wrapper used by legacy /api/pci and /api/pci/live."""
    plant_id = _active_plant()
    snapshot = _tenant_snapshot(plant_id)
    if snapshot is not None:
        return snapshot
    return original_getter()


def install() -> bool:
    """Patch only the simulator's snapshot function at application bootstrap."""
    try:
        import pci_live_simulator as simulator
        original = getattr(simulator, "get_live_pci_snapshot", None)
        if original is None or getattr(original, "_anviqo_universal_adapter", False):
            return False

        def tenant_snapshot():
            return get_live_pci_snapshot(original)

        tenant_snapshot._anviqo_universal_adapter = True
        tenant_snapshot._anviqo_original = original
        simulator.get_live_pci_snapshot = tenant_snapshot
        return True
    except Exception:
        return False


INSTALLED = install()
