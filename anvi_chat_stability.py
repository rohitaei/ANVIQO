"""ANVIQO chat stability layer.

Adds a tenant-scoped exact-tag fallback around the existing tenant chat boundary.
It searches tag, external_id and evidence fields using normalized engineering
identifiers, chooses the richest matching row, and converts unexpected query
errors into evidence-safe responses. It does not touch importer, V5, PCI, PLC,
or SCADA control paths.
"""
from __future__ import annotations

import json
import os
import re

SAFETY = {
    "tenant_scoped": True,
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
}

_NAMES = (
    "knowledge_id","organization_id","plant_id","document_id","record_type",
    "external_id","name","area","service","asset_type","tag","parent_id",
    "source","metadata","content","created_at"
)

_PREFIXES = {
    "PT","TT","FT","LT","AT","DT","ST","WT","CT","TE","PE","FE",
    "LE","AE","AI","AO","DI","DO","XV","FV","PV","TV","LV","ZV",
    "ZS","ZSO","ZSC","PS","TS","LS","FS","AS","HS","CS","ES","IS",
    "MS","SS","VB","PC","FC"
}


def _norm(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _candidate(q):
    for token in re.findall(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b", str(q or "")):
        n = _norm(token)
        m = re.match(r"[A-Z]+", n)
        if m and m.group(0) in _PREFIXES:
            return n
    return None


def _store():
    try:
        import anvi_tenant_store as store
        url = os.getenv("ANVIQO_TENANT_DB_URL", "").strip() or os.getenv("DATABASE_URL", "").strip()
        if url and not url.startswith("sqlite:") and "sslmode=" not in url.lower():
            os.environ["ANVIQO_TENANT_DB_URL"] = url + ("&" if "?" in url else "?") + "sslmode=require"
        if store.enabled():
            return store
    except Exception:
        pass
    return None


def _row(row):
    if isinstance(row, dict):
        item = dict(row)
    elif hasattr(row, "keys"):
        try:
            item = {k: row[k] for k in row.keys()}
        except Exception:
            item = {}
    elif isinstance(row, (tuple, list)):
        item = dict(zip(_NAMES, row))
    else:
        item = {}
    meta = item.get("metadata")
    if isinstance(meta, str):
        try:
            item["metadata"] = json.loads(meta)
        except Exception:
            item["metadata"] = {}
    return item


def _richness(row):
    r = _row(row)
    score = 0
    for key in ("tag","external_id","name","area","service","asset_type","record_type","source","content"):
        if str(r.get(key) or "").strip():
            score += 1
    meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
    score += sum(1 for k in ("io_type","i_o_type","plc_address","panel","tb","jb","range","unit","model","criticality") if meta.get(k) not in (None,""))
    return score


def _field(row):
    row = _row(row)
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    vals = []
    for key, label in (("tag","Tag"),("external_id","External ID"),("name","Instrument/service"),("area","Area"),("source","Source")):
        if row.get(key):
            vals.append(f"{label}: {row[key]}")
    for key, label in (("io_type","I/O"),("i_o_type","I/O"),("plc_address","PLC"),("panel","Panel"),("tb","TB"),("jb","JB"),("range","Range"),("unit","Unit"),("model","Model"),("criticality","Criticality")):
        if meta.get(key) not in (None,""):
            vals.append(f"{label}: {meta[key]}")
    return "; ".join(vals)


def _exact(plant_id, identifier):
    store = _store()
    if not store or not plant_id or not identifier:
        return None
    p = store._placeholder()
    fields = "knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content,created_at"
    normalized = _norm(identifier)
    sql = f"""
        SELECT {fields}
        FROM anviqo_plant_knowledge
        WHERE plant_id={p}
          AND (
            regexp_replace(upper(coalesce(tag,'')), '[^A-Z0-9]', '', 'g')={p}
            OR regexp_replace(upper(coalesce(external_id,'')), '[^A-Z0-9]', '', 'g')={p}
            OR regexp_replace(upper(coalesce(name,'')), '[^A-Z0-9]', '', 'g')={p}
            OR regexp_replace(upper(coalesce(service,'')), '[^A-Z0-9]', '', 'g')={p}
            OR regexp_replace(upper(coalesce(content,'')), '[^A-Z0-9]', '', 'g') LIKE {p}
          )
        ORDER BY created_at DESC, knowledge_id DESC
        LIMIT 50
    """
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, (plant_id, normalized, normalized, normalized, normalized, "%" + normalized + "%"))
        rows = [_row(r) for r in cur.fetchall()]
    if not rows:
        return None
    rows.sort(key=_richness, reverse=True)
    return rows[0]


def _safe(answer, **extra):
    payload = {"answer": answer, **SAFETY}
    payload.update(extra)
    return payload


def install():
    try:
        import anvi_knowledge_layer as knowledge
        from flask import session
    except Exception:
        return
    current = getattr(knowledge, "ask_anvi", None)
    if not callable(current) or getattr(current, "_anviqo_chat_stability", False):
        return

    def wrapped(q, *args, **kwargs):
        text = str(q or "")
        plant_id = session.get("plant_id")
        org_id = session.get("organization_id")
        candidate = _candidate(text)
        if plant_id and candidate:
            try:
                hit = _exact(plant_id, candidate)
                if hit and (not org_id or str(hit.get("organization_id")) == str(org_id)):
                    shown = hit.get("tag") or hit.get("external_id") or candidate
                    return _safe(
                        "Verified tenant knowledge for " + str(shown) + ": " + _field(hit),
                        blocked=False,
                        evidence_status="EVIDENCE_AVAILABLE",
                        plant_id=plant_id,
                        plant_name=None,
                        evidence=[hit],
                    )
            except Exception:
                # Never expose a database failure as a 5xx chat failure.
                pass
        try:
            result = current(q, *args, **kwargs)
            return result
        except Exception as exc:
            if plant_id:
                return _safe(
                    "ANVI could not complete that plant-knowledge query. No other plant's data was used. Please retry the same question.",
                    blocked=True,
                    reason="TENANT_QUERY_ERROR",
                    plant_id=plant_id,
                    error_type=type(exc).__name__,
                )
            return _safe("No plant is selected. Select a plant before asking plant-specific questions.", blocked=True, reason="NO_ACTIVE_PLANT")

    wrapped._anviqo_chat_stability = True
    knowledge.ask_anvi = wrapped


__all__ = ["install"]
