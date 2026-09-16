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
        cur.execute(f"SELECT plant_id,organization_id,name,slug,status FROM anviqo_plants WHERE plant_id={p}", (plant_id,))
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
        cur.execute(f"SELECT knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content,created_at FROM anviqo_plant_knowledge WHERE plant_id={p} ORDER BY created_at,knowledge_id", (plant_id,))
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
    return str(plant.get("slug", "")).strip().lower() == "primary-plant"


def _safe_response(answer: str, **extra):
    payload = {"answer": answer, "tenant_scoped": True, "read_only": True, "plc_write": False, "scada_control": False, "human_decision_required": True}
    payload.update(extra)
    return payload


_ENGINEERING_PREFIXES = {"PT", "TT", "FT", "LT", "AT", "DT", "ST", "WT", "CT", "TE", "PE", "FE", "LE", "AE", "AI", "AO", "DI", "DO", "XV", "FV", "PV", "TV", "LV", "ZV", "ZS", "ZSO", "ZSC", "PS", "TS", "LS", "FS", "AS", "HS", "CS", "ES", "IS", "MS", "SS", "VB", "PC", "FC"}


def _tag_from_question(q: str, rows: list[dict] | None = None):
    """Return an explicit engineering tag, but do not mistake plant names such as MBF-2 for tags."""
    known = set()
    for r in rows or []:
        for key in ("tag", "external_id"):
            value = r.get(key)
            if value:
                known.add(_normalize(value))
    for token in re.findall(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b", q or ""):
        n = _normalize(token)
        if not n:
            continue
        if n in known:
            return n
        prefix_match = re.match(r"[A-Z]+", n)
        prefix = prefix_match.group(0) if prefix_match else ""
        if prefix in _ENGINEERING_PREFIXES:
            return n
    return None


def _question_terms(text: str):
    stop = {"what", "tell", "me", "about", "do", "you", "have", "the", "for", "and", "to", "in", "of", "is", "are", "available", "information", "this", "that", "plant", "please", "give", "show", "can", "i", "we", "my", "your", "on", "from", "with", "currently", "selected", "knowledge"}
    terms = []
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_./-]{1,}", text.lower()):
        n = _normalize(raw)
        if len(n) >= 2 and raw not in stop and n not in {_normalize(x) for x in stop}:
            terms.append(raw)
    return list(dict.fromkeys(terms))


def _natural_knowledge_answer(text: str, rows: list[dict], plant: dict):
    terms = _question_terms(text)
    if not terms:
        return None
    matches = []
    for row in rows:
        hay = " ".join(str(row.get(k) or "") for k in ("external_id", "name", "area", "service", "asset_type", "tag", "source", "content")).lower()
        score = sum(1 for term in terms if term in hay)
        if score:
            matches.append((score, row))
    if not matches:
        return None
    # knowledge_id is an opaque PostgreSQL string such as know_00031..., not an integer.
    matches.sort(key=lambda x: (-x[0], str(x[1].get("knowledge_id") or "")))
    top = [r for _, r in matches[:12]]
    sources = {}
    for r in matches:
        src = str(r.get("source") or "UNKNOWN")
        sources[src] = sources.get(src, 0) + 1
    source_text = "; ".join(f"{name}: {count} matching record(s)" for name, count in list(sources.items())[:6])
    lines = [f"I found {len(matches)} matching knowledge record(s) in the selected plant {plant['name']}, using only its onboarded data.", f"Sources: {source_text}.", "Representative evidence:"]
    for r in top[:8]:
        label = r.get("tag") or r.get("external_id") or r.get("name") or "record"
        desc = r.get("name") or r.get("service") or r.get("record_type") or "knowledge record"
        lines.append(f"{label} — {desc}; Area: {r.get('area') or 'UNKNOWN'}; Source: {r.get('source') or 'UNKNOWN'}")
    return _safe_response("\n".join(lines), blocked=False, evidence_status="EVIDENCE_AVAILABLE", plant_id=plant["plant_id"], plant_name=plant["name"], count=len(matches), evidence=top[:8])


def _tenant_answer(q: str, rows: list[dict], plant: dict):
    text = str(q or "").strip()
    low = text.lower()
    normalized_tags = {_normalize(r.get("tag")): r for r in rows if r.get("tag")}
    if any(x in low for x in ("what plant", "which plant", "connected to", "current plant", "selected plant")):
        return _safe_response(f"ANVI is connected to {plant['name']} (selected plant).", plant_id=plant["plant_id"], plant_name=plant["name"])
    requested = _tag_from_question(text, rows)
    if requested:
        row = normalized_tags.get(requested)
        if not row:
            return _safe_response("I cannot find that tag in the currently selected plant's knowledge. I will not use another plant's data as a fallback.", blocked=True, reason="TENANT_KNOWLEDGE_NOT_FOUND", plant_id=plant["plant_id"], plant_name=plant["name"])
        fields = {"tag": row.get("tag"), "name": row.get("name"), "area": row.get("area"), "service": row.get("service"), "asset_type": row.get("asset_type"), "record_type": row.get("record_type"), "external_id": row.get("external_id"), "parent_id": row.get("parent_id"), "source": row.get("source")}
        meta = row.get("metadata")
        if isinstance(meta, dict):
            for key in ("io_type", "i_o_type", "plc_address", "panel", "tb", "criticality", "model", "range", "unit"):
                if meta.get(key) is not None:
                    fields[key] = meta[key]
        fields = {k: v for k, v in fields.items() if v not in (None, "", [])}
        return _safe_response(f"Verified tenant knowledge for {row.get('tag') or row.get('name')}: " + ", ".join(f"{k}: {v}" for k, v in fields.items() if k != "tag"), blocked=False, evidence_status="EVIDENCE_AVAILABLE", plant_id=plant["plant_id"], plant_name=plant["name"], evidence=[fields])
    if any(x in low for x in ("count", "how many", "number of")) and any(x in low for x in ("equipment", "instrument", "io", "i/o", "asset", "device")):
        usable = [r for r in rows if r.get("tag") or str(r.get("record_type") or "").lower() in {"instrument", "io", "pci", "asset"}]
        distinct = {(_normalize(r.get("tag")) or str(r.get("external_id") or r.get("knowledge_id"))) for r in usable}
        distinct.discard("")
        return _safe_response(f"The selected plant {plant['name']} has {len(distinct)} indexed equipment/instrument records in tenant knowledge.", blocked=False, evidence_status="EVIDENCE_AVAILABLE", plant_id=plant["plant_id"], plant_name=plant["name"], count=len(distinct))
    natural = _natural_knowledge_answer(text, rows, plant)
    if natural is not None:
        return natural
    if rows:
        return None
    return _safe_response(f"The selected plant {plant['name']} has no indexed onboarding knowledge yet. I will not use another plant's data as a fallback.", blocked=True, reason="TENANT_ONBOARDING_NOT_READY", plant_id=plant["plant_id"], plant_name=plant["name"])


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
            return _safe_response("No plant is selected. Select a plant before asking plant-specific questions.", blocked=True, reason="NO_ACTIVE_PLANT")
        plant = _plant(plant_id)
        if not plant or (organization_id and plant.get("organization_id") != organization_id):
            return _safe_response("The selected plant context is invalid. I will not access plant data.", blocked=True, reason="INVALID_PLANT_CONTEXT")
        if _legacy(plant):
            return original(q, *args, **kwargs)
        rows = _rows(plant_id)
        result = _tenant_answer(q, rows, plant)
        if result is not None:
            return result
        return _safe_response("I can only answer from the currently selected plant's onboarded knowledge. That information is not available in this plant yet, so I will not use another plant's data as a fallback.", blocked=True, reason="TENANT_SCOPE_ONLY", plant_id=plant["plant_id"], plant_name=plant["name"])
    wrapped._anviqo_tenant_boundary = True
    knowledge.ask_anvi = wrapped


install()
