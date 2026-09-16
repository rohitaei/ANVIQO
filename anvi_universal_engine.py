"""ANVIQO Universal Plant Engine.

One tenant-neutral readiness/intelligence layer for every newly onboarded plant.
It never imports or modifies V5 intelligence and never enables PLC/SCADA writes.
The engine derives readiness from the selected plant's own normalized knowledge,
so no plant-specific reasoning code is required.
"""
from __future__ import annotations

import json
from flask import jsonify, Response

SAFETY = {
    "v5_intelligence_modified": False,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "read_only": True,
}


def _store():
    try:
        import anvi_tenant_store as store
        if store.enabled():
            return store
    except Exception:
        pass
    return None


def _row(row, names):
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "keys"):
        try:
            return {k: row[k] for k in row.keys()}
        except Exception:
            pass
    if isinstance(row, (tuple, list)):
        return dict(zip(names, row))
    return {}


def _metadata(row):
    value = row.get("metadata")
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return {}


def _normalize(value):
    import re
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def readiness(plant_id):
    """Return deterministic, tenant-scoped readiness derived from stored data."""
    store = _store()
    if not store or not plant_id:
        return {"status": "NOT_READY", "reason": "TENANT_STORE_UNAVAILABLE", **SAFETY}
    p = store._placeholder()
    names = ("knowledge_id", "document_id", "record_type", "external_id", "name", "area", "service", "asset_type", "tag", "source", "metadata", "content")
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT name,slug,status FROM anviqo_plants WHERE plant_id={p} LIMIT 1", (plant_id,))
        plant_row = cur.fetchone()
        if not plant_row:
            return {"status": "NOT_READY", "reason": "PLANT_NOT_FOUND", "plant_id": plant_id, **SAFETY}
        plant = _row(plant_row, ("name", "slug", "status"))
        cur.execute(f"SELECT count(*) FROM anviqo_plant_documents WHERE plant_id={p}", (plant_id,))
        document_count = int((cur.fetchone() or [0])[0])
        cur.execute(f"SELECT count(*) FROM anviqo_plant_knowledge WHERE plant_id={p}", (plant_id,))
        knowledge_count = int((cur.fetchone() or [0])[0])
        cur.execute(f"SELECT count(DISTINCT source) FROM anviqo_plant_knowledge WHERE plant_id={p} AND coalesce(source,'')<>''", (plant_id,))
        source_count = int((cur.fetchone() or [0])[0])
        cur.execute(f"SELECT count(DISTINCT area) FROM anviqo_plant_knowledge WHERE plant_id={p} AND coalesce(area,'')<>''", (plant_id,))
        area_count = int((cur.fetchone() or [0])[0])
        cur.execute(f"SELECT count(DISTINCT tag) FROM anviqo_plant_knowledge WHERE plant_id={p} AND coalesce(tag,'')<>''", (plant_id,))
        tag_count = int((cur.fetchone() or [0])[0])
    ready = document_count > 0 and knowledge_count > 0
    return {
        "status": "READY" if ready else "WAITING_FOR_DATA",
        "plant_id": plant_id,
        "plant_name": plant.get("name", ""),
        "plant_status": plant.get("status", ""),
        "documents": document_count,
        "knowledge_records": knowledge_count,
        "source_documents": source_count,
        "areas": area_count,
        "indexed_tags": tag_count,
        "capabilities": {
            "natural_language_chat": ready,
            "tag_lookup": ready,
            "instrument_lookup": ready,
            "plc_io_lookup": ready,
            "source_evidence": ready,
            "plant_health": ready,
            "events": ready,
            "maintenance_context": ready,
            "reports": ready,
            "critical_spares": True,
        },
        "acceptance": {
            "plant_created": True,
            "documents_present": document_count > 0,
            "knowledge_records_gt_zero": knowledge_count > 0,
            "answer_layer_ready": ready,
        },
        **SAFETY,
    }


def register(app):
    """Register universal engine endpoints on the existing ANVIQO app."""
    # Install the final tenant-safe chat guard after the existing boundary layer.
    try:
        import anvi_chat_stability as _chat_stability
        _chat_stability.install()
    except Exception:
        pass
    if getattr(app, "_anvi_universal_engine_registered", False):
        return

    @app.get("/api/admin/anvi-engine/readiness/<plant_id>")
    def anvi_engine_readiness(plant_id):
        # Reuse onboarding's authenticated actor when available; fail closed otherwise.
        try:
            from flask import session
            user = session.get("user_id")
            org = session.get("organization_id")
            role = session.get("role")
            if not user or not org or role not in {"OWNER", "ADMIN"}:
                return jsonify({"status": "FORBIDDEN"}), 403
            store = _store()
            p = store._placeholder()
            with store._connect() as conn:
                cur = conn.cursor()
                cur.execute(f"SELECT 1 FROM anviqo_plants WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE' LIMIT 1", (plant_id, org))
                if not cur.fetchone():
                    return jsonify({"status": "FORBIDDEN"}), 403
        except Exception:
            return jsonify({"status": "FORBIDDEN"}), 403
        return jsonify(readiness(plant_id))

    app._anvi_universal_engine_registered = True


__all__ = ["readiness", "register"]
