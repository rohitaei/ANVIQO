"""ANVIQO tenant chat boundary.

Presentation/routing layer only. It does not replace or modify V5 intelligence.
For a selected non-legacy plant, chat is fail-closed to that plant's indexed
knowledge and never falls back to the global V5/PCI database.
"""
from __future__ import annotations

import json
import os
import re


def _normalize(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _session_context():
    try:
        from flask import session
        return session.get("plant_id"), session.get("organization_id")
    except Exception:
        return None, None


def _prepare_tenant_db_url():
    """Render PostgreSQL requires TLS; make the tenant store explicit about it."""
    url = os.getenv("ANVIQO_TENANT_DB_URL", "").strip() or os.getenv("DATABASE_URL", "").strip()
    if not url or url.startswith("sqlite:"):
        return
    lower = url.lower()
    if "sslmode=" in lower:
        return
    separator = "&" if "?" in url else "?"
    os.environ["ANVIQO_TENANT_DB_URL"] = url + separator + "sslmode=require"


def _tenant_store():
    _prepare_tenant_db_url()
    import anvi_tenant_store as store
    if not store.enabled():
        return None
    store.init_schema()
    return store


def _plant(plant_id: str):
    store = _tenant_store()
    if not store or not plant_id:
        return None
    p = store._placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT plant_id,organization_id,name,slug,status FROM anviqo_plants WHERE plant_id={p}",
            (plant_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return dict(zip(("plant_id", "organization_id", "name", "slug", "status"), row))


def _rows(plant_id: str):
    store = _tenant_store()
    if not store or not plant_id:
        return []
    p = store._placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content,created_at FROM anviqo_plant_knowledge WHERE plant_id={p} ORDER BY created_at,knowledge_id",
            (plant_id,),
        )
        raw = cur.fetchall()
    names = ("knowledge_id", "organization_id", "plant_id", "document_id", "record_type", "external_id", "name", "area", "service", "asset_type", "tag", "parent_id", "source", "metadata", "content", "created_at")
    result = []
    for row in raw:
        item = dict(zip(names, row))
        meta = item.get("metadata")
        if isinstance(meta, str):
            try:
                item["metadata"] = json.loads(meta)
            except Exception:
                pass
        result.append(item)
    return result


def _legacy(plant: dict | None) -> bool:
    if not plant:
        return False
    # Bootstrap Primary Plant is the only compatibility exception. New plants
    # are always tenant-only until explicitly migrated in a future phase.
    return str(plant.get("slug", "")).strip().lower() == "primary-plant"


def _safe_response(answer: str, **extra):
    payload = {
        "answer": answer,
        "tenant_scoped": True,
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "human_decision_required": True,
    }
    payload.update(extra)
    return payload


def _tag_from_question(q: str):
    # Prefer explicit engineering tag-like tokens. Resolver remains owned by V5;
    # this boundary only identifies a tenant row and never invents identity.
    for token in re.findall(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b", q or ""):
        n = _normalize(token)
        if n:
            return n
    return None


def _tenant_answer(q: str, rows: list[dict], plant: dict):
    text = str(q or "").strip()
    low = text.lower()
    normalized_tags = {_normalize(r.get("tag")): r for r in rows if r.get("tag")}

    if any(x in low for x in ("what plant", "which plant", "connected to", "current plant", "selected plant")):
        return _safe_response(
            f"ANVI is connected to {plant['name']} (selected plant).",
            plant_id=plant["plant_id"],
            plant_name=plant["name"],
        )

    requested = _tag_from_question(text)
    if requested:
        row = normalized_tags.get(requested)
        if not row:
            return _safe_response(
                "I cannot find that tag in the currently selected plant's knowledge. "
                "I will not use another plant's data as a fallback.",
                blocked=True,
                reason="TENANT_KNOWLEDGE_NOT_FOUND",
                plant_id=plant["plant_id"],
                plant_name=plant["name"],
            )
        fields = {
            "tag": row.get("tag"),
            "name": row.get("name"),
            "area": row.get("area"),
            "service": row.get("service"),
            "asset_type": row.get("asset_type"),
            "record_type": row.get("record_type"),
            "external_id": row.get("external_id"),
            "parent_id": row.get("parent_id"),
            "source": row.get("source"),
        }
        meta = row.get("metadata")
        if isinstance(meta, dict):
            for key in ("io_type", "i_o_type", "plc_address", "panel", "tb", "criticality", "model", "range", "unit"):
                if meta.get(key) is not None:
                    fields[key] = meta[key]
        fields = {k: v for k, v in fields.items() if v not in (None, "", [])}
        return _safe_response(
            f"Verified tenant knowledge for {row.get('tag') or row.get('name')}: "
            + ", ".join(f"{k}: {v}" for k, v in fields.items() if k != "tag"),
            blocked=False,
            evidence_status="EVIDENCE_AVAILABLE",
            plant_id=plant["plant_id"],
            plant_name=plant["name"],
            evidence=[fields],
        )

    if any(x in low for x in ("count", "how many", "number of")) and any(x in low for x in ("equipment", "instrument", "io", "i/o", "asset", "device")):
        usable = [r for r in rows if r.get("tag") or str(r.get("record_type") or "").lower() in {"instrument", "io", "pci", "asset"}]
        distinct = {(_normalize(r.get("tag")) or str(r.get("external_id") or r.get("knowledge_id"))) for r in usable}
        distinct.discard("")
        return _safe_response(
            f"The selected plant {plant['name']} has {len(distinct)} indexed equipment/instrument records in tenant knowledge.",
            blocked=False,
            evidence_status="EVIDENCE_AVAILABLE",
            plant_id=plant["plant_id"],
            plant_name=plant["name"],
            count=len(distinct),
        )

    if rows:
        return None
    return _safe_response(
        f"The selected plant {plant['name']} has no indexed onboarding knowledge yet. "
        "I will not use another plant's data as a fallback.",
        blocked=True,
        reason="TENANT_ONBOARDING_NOT_READY",
        plant_id=plant["plant_id"],
        plant_name=plant["name"],
    )


def install():
    try:
        _prepare_tenant_db_url()
        import anvi_knowledge_layer as knowledge
    except Exception:
        return
    original = getattr(knowledge, "ask_anvi", None)
    if not callable(original) or getattr(original, "_anviqo_tenant_boundary", False):
        return

    def wrapped(q, *args, **kwargs):
        plant_id, organization_id = _session_context()
        if not plant_id:
            return _safe_response(
                "No plant is selected. Select a plant before asking plant-specific questions.",
                blocked=True,
                reason="NO_ACTIVE_PLANT",
            )
        plant = _plant(plant_id)
        if not plant or (organization_id and plant.get("organization_id") != organization_id):
            return _safe_response(
                "The selected plant context is invalid. I will not access plant data.",
                blocked=True,
                reason="INVALID_PLANT_CONTEXT",
            )
        if _legacy(plant):
            return original(q, *args, **kwargs)
        rows = _rows(plant_id)
        result = _tenant_answer(q, rows, plant)
        if result is not None:
            return result
        return _safe_response(
            "I can only answer from the currently selected plant's onboarded knowledge. "
            "That information is not available in this plant yet, so I will not use another plant's data as a fallback.",
            blocked=True,
            reason="TENANT_SCOPE_ONLY",
            plant_id=plant["plant_id"],
            plant_name=plant["name"],
        )

    wrapped._anviqo_tenant_boundary = True
    knowledge.ask_anvi = wrapped


install()
