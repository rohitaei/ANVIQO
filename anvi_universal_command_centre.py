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
    # Reuse the existing PCI simulator for the explicitly simulated PCI tenant.
    # Tenant evidence/identity remains authoritative; this only supplies
    # simulated value, health, change and event state. No PLC/SCADA action.
    simulator = None
    simulation_enabled = False
    try:
        from flask import has_request_context, session
        organization_id = str(session.get("organization_id") or "").strip() if has_request_context() else ""
        import anvi_verified_pci_adapter as pci_adapter
        simulation_enabled = pci_adapter.is_bound(plant_id, organization_id or None)
        if simulation_enabled:
            import pci_live_simulator as simulator
    except Exception:
        simulator = None
        simulation_enabled = False
    healthy = warning = critical = changed = active_events = 0
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
        if simulation_enabled and simulator is not None:
            try:
                sim_record = {
                    "tag": point["tag"],
                    "description": point["name"],
                    "area": point["area"],
                    "io_type": metadata.get("io_type") or metadata.get("I/O") or point["asset_type"],
                    "plc_address": metadata.get("plc_address") or metadata.get("plc"),
                    "panel": metadata.get("panel"),
                }
                sim = simulator.simulate_point(sim_record)
                point.update({
                    "status": sim["state"],
                    "state": sim["state"],
                    "mode": "SIMULATION",
                    "value": sim["value"],
                    "changed": sim["changed"],
                    "event_active": sim["event_active"],
                    "timestamp": sim["timestamp"],
                    "simulation_source": sim["source"],
                })
            except Exception:
                pass
        points.append(point)
        state = point["state"]
        if state == "HEALTHY":
            healthy += 1
        elif state == "WARNING":
            warning += 1
        elif state == "CRITICAL":
            critical += 1
        if point.get("changed"):
            changed += 1
        if point.get("event_active"):
            active_events += 1
        area_name = str(area or "GENERAL") or "GENERAL"
        bucket = areas.setdefault(area_name, {"name": area_name, "count": 0, "healthy": 0, "warning": 0, "critical": 0})
        bucket["count"] += 1
        if state == "HEALTHY":
            bucket["healthy"] += 1
        elif state == "WARNING":
            bucket["warning"] += 1
        elif state == "CRITICAL":
            bucket["critical"] += 1

    area_list = list(areas.values())
    is_simulation = bool(points) and any(p.get("mode") == "SIMULATION" for p in points)
    plant_score = ((healthy + warning * 0.5) / len(points)) * 100 if points and is_simulation else None
    return {
        "status": "OK",
        "mode": "SIMULATION" if is_simulation else "ONBOARDING_DATA",
        "source": "PCI DEMO STREAM" if is_simulation else "ANVIQO TENANT PLANT KNOWLEDGE",
        "total_io": len(points),
        "healthy": healthy if is_simulation else 0,
        "warning": warning if is_simulation else 0,
        "critical": critical if is_simulation else 0,
        "critical_count": critical if is_simulation else 0,
        "changed": changed if is_simulation else 0,
        "active_events": active_events if is_simulation else [],
        "plant_health_score": round(plant_score, 2) if plant_score is not None else None,
        "health_status": "SIMULATED" if is_simulation else "DATA_ONLY",
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

    # Once a tenant is selected, never fall back to the bootstrap/demo
    # simulator. An empty tenant must remain empty rather than showing
    # another plant's evidence.
    if plant_id:
        snapshot = _tenant_snapshot(plant_id)
        if snapshot is not None:
            return snapshot
        return {
            "status": "NO DATA",
            "mode": "ONBOARDING_DATA",
            "source": "ANVIQO TENANT PLANT KNOWLEDGE",
            "total_io": 0,
            "healthy": 0,
            "warning": 0,
            "critical": 0,
            "critical_count": 0,
            "changed": 0,
            "active_events": [],
            "plant_health_score": None,
            "health_status": "NO DATA",
            "area_count": 0,
            "areas": [],
            "points": [],
            "records": [],
            "plant_id": plant_id,
            "safety": dict(SAFETY),
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }

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
