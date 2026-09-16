"""Universal, tenant-safe ANVI answer engine.

This layer is the common answer path for every onboarded plant. It resolves
engineering identifiers and natural-language knowledge questions directly from
the selected plant's normalized knowledge store. It never falls back to a
legacy/global plant for a plant-specific question and never enables PLC/SCADA
control.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

SAFETY = {
    "tenant_scoped": True,
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
}

NAMES = (
    "knowledge_id", "organization_id", "plant_id", "document_id", "record_type",
    "external_id", "name", "area", "service", "asset_type", "tag", "parent_id",
    "source", "metadata", "content", "created_at",
)

PREFIXES = {
    "PT", "TT", "FT", "LT", "AT", "DT", "ST", "WT", "CT", "TE", "PE", "FE",
    "LE", "AE", "AI", "AO", "DI", "DO", "XV", "FV", "PV", "TV", "LV", "ZV",
    "ZS", "ZSO", "ZSC", "PS", "TS", "LS", "FS", "AS", "HS", "CS", "ES", "IS",
    "MS", "SS", "VB", "PC", "FC",
}

STOP = {
    "what", "tell", "me", "about", "do", "you", "have", "the", "for", "and", "to",
    "in", "of", "is", "are", "available", "information", "this", "that", "plant",
    "please", "give", "show", "can", "i", "we", "my", "your", "on", "from", "with",
    "currently", "selected", "knowledge", "including", "their", "documents", "details",
    "instrument", "instruments", "source", "sources", "data",
}


def _norm(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _candidate(text):
    for token in re.findall(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b", str(text or "")):
        normalized = _norm(token)
        match = re.match(r"[A-Z]+", normalized)
        if match and match.group(0) in PREFIXES:
            return normalized
    return None


def _terms(text):
    out = []
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_./-]{1,}", str(text or "").lower()):
        if raw in STOP:
            continue
        if len(_norm(raw)) >= 2:
            out.append(raw)
    return list(dict.fromkeys(out))


def _store():
    try:
        import anvi_tenant_store as store
        url = os.getenv("ANVIQO_TENANT_DB_URL", "").strip() or os.getenv("DATABASE_URL", "").strip()
        if url and not url.startswith("sqlite:") and "sslmode=" not in url.lower():
            os.environ["ANVIQO_TENANT_DB_URL"] = url + ("&" if "?" in url else "?") + "sslmode=require"
        if store.enabled():
            return store
    except Exception:
        return None
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
        item = dict(zip(NAMES, row))
    else:
        item = {}
    meta = item.get("metadata")
    if isinstance(meta, str):
        try:
            item["metadata"] = json.loads(meta)
        except Exception:
            item["metadata"] = {}
    return item


def _safe(answer, **extra):
    payload = {"answer": answer, **SAFETY}
    payload.update(extra)
    return payload


def _field(row):
    row = _row(row)
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    vals = []
    for key, label in (("tag", "Tag"), ("external_id", "External ID"), ("name", "Instrument/service"),
                       ("area", "Area"), ("source", "Source")):
        if row.get(key):
            vals.append(f"{label}: {row[key]}")
    for key, label in (("io_type", "I/O"), ("i_o_type", "I/O"), ("plc_address", "PLC"),
                       ("panel", "Panel"), ("tb", "TB"), ("jb", "JB"), ("range", "Range"),
                       ("unit", "Unit"), ("model", "Model"), ("criticality", "Criticality")):
        if meta.get(key) not in (None, ""):
            vals.append(f"{label}: {meta[key]}")
    return "; ".join(vals)


def _richness(row):
    row = _row(row)
    score = sum(bool(str(row.get(k) or "").strip()) for k in
                ("tag", "external_id", "name", "area", "service", "asset_type", "record_type", "source", "content"))
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    score += sum(meta.get(k) not in (None, "") for k in
                 ("io_type", "i_o_type", "plc_address", "panel", "tb", "jb", "range", "unit", "model", "criticality"))
    return score


def _query_rows(plant_id, organization_id, identifier=None, terms=None, limit=120):
    store = _store()
    if not store or not plant_id:
        raise RuntimeError("TENANT_STORE_UNAVAILABLE")
    p = store._placeholder()
    fields = ",".join(NAMES)
    clauses = [f"plant_id={p}"]
    params = [plant_id]
    if organization_id:
        clauses.append(f"organization_id={p}")
        params.append(organization_id)
    if identifier:
        n = _norm(identifier)
        clauses.append("(" + " OR ".join(
            f"regexp_replace(upper(coalesce({c},'')), '[^A-Z0-9]', '', 'g')={p}"
            for c in ("tag", "external_id", "name", "service")
        ) + " OR regexp_replace(upper(coalesce(content,'')), '[^A-Z0-9]', '', 'g') LIKE " + p + ")")
        params.extend([n] * 5)
        order = "created_at DESC, knowledge_id DESC"
    else:
        terms = list(terms or [])[:10]
        category_terms = {"pressure", "temperature", "temp", "flow", "level", "instrument", "instruments"}
        context_terms = [t for t in terms if t not in category_terms]
        if context_terms:
            for term in context_terms:
                like = f"%{str(term).replace('%', '')}%"
                clauses.append("(" + " OR ".join(
                    f"lower(coalesce({c},'')) LIKE {p}" for c in
                    ("external_id", "name", "area", "service", "asset_type", "tag", "source", "content")
                ) + ")")
                params.extend([like] * 8)
        wanted = [t for t in terms if t in category_terms]
        if wanted:
            category_clause = []
            for term in wanted:
                like = f"%{str(term).replace('%', '')}%"
                category_clause.append("(" + " OR ".join(
                    f"lower(coalesce({c},'')) LIKE {p}" for c in
                    ("name", "service", "asset_type", "tag", "content")
                ) + ")")
                params.extend([like] * 5)
            clauses.append("(" + " OR ".join(category_clause) + ")")
        if not context_terms and not wanted:
            clauses.append("1=0")
        order = "created_at DESC, knowledge_id DESC"
    sql = f"SELECT {fields} FROM anviqo_plant_knowledge WHERE {' AND '.join(clauses)} ORDER BY {order} LIMIT {int(limit)}"
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        return [_row(r) for r in cur.fetchall()]


def _plant_context():
    try:
        from flask import session
        return session.get("plant_id"), session.get("organization_id")
    except Exception:
        return None, None


def _plant(plant_id, organization_id):
    store = _store()
    if not store or not plant_id:
        return None
    p = store._placeholder()
    clauses = [f"plant_id={p}"]
    params = [plant_id]
    if organization_id:
        clauses.append(f"organization_id={p}")
        params.append(organization_id)
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT plant_id,organization_id,name,slug,status FROM anviqo_plants WHERE {' AND '.join(clauses)} LIMIT 1", tuple(params))
        row = cur.fetchone()
    return _row(row) if row else None


def _is_data_question(text):
    low = text.lower()
    return bool(_candidate(text) or any(x in low for x in (
        "instrument", "pressure", "temperature", "flow", "level", "plc", "i/o", " io ",
        "equipment", "tag", "panel", "terminal", "tb", "jb", "cable", "source document",
        "onboard", "knowledge", "plant data", "what changed", "maintenance", "spare",
        "alarm", "event", "plant health", "health", "shift report", "report",
    )))


def _io_kind(row):
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    value = " ".join(str(row.get(k) or "") for k in ("record_type", "asset_type", "name", "service", "content"))
    value += " " + str(meta.get("io_type") or meta.get("i_o_type") or "")
    u = " " + re.sub(r"[^A-Z0-9-]+", " ", value.upper()) + " "
    if " DIGITAL INPUT " in u or " DI " in u: return "DI"
    if " DIGITAL OUTPUT " in u or " DO " in u: return "DO"
    if " ANALOG OUTPUT " in u or " AO " in u: return "AO"
    if " ANALOG INPUT " in u or " AI " in u or "4-20 MA" in u or " RTD " in u: return "AI"
    return "Other"


def _category(row):
    text = " ".join(str(row.get(k) or "") for k in ("tag", "name", "service", "asset_type", "content")).upper()
    if "PRESSURE" in text or re.search(r"\bPT[_ -]?\d", text): return "Pressure"
    if any(x in text for x in ("TEMPERATURE", "TEMP", "THERMOCOUPLE", "RTD")) or re.search(r"\bTT[_ -]?\d", text): return "Temperature"
    if "FLOW" in text or re.search(r"\bFT[_ -]?\d", text): return "Flow"
    if "LEVEL" in text or re.search(r"\bLT[_ -]?\d", text): return "Level"
    return None


def _exact_answer(text, rows, plant):
    requested = _candidate(text)
    if not requested:
        return None
    exact = [r for r in rows if any(_norm(r.get(k)) == requested for k in ("tag", "external_id", "name", "service"))]
    if not exact:
        exact = [r for r in rows if requested in _norm(r.get("content"))]
    if not exact:
        return _safe(
            "I cannot find that tag in the currently selected plant's knowledge. I will not use another plant's data as a fallback.",
            blocked=True, reason="TENANT_KNOWLEDGE_NOT_FOUND", plant_id=plant["plant_id"], plant_name=plant.get("name"),
        )
    row = max(exact, key=_richness)
    shown = row.get("tag") or row.get("external_id") or requested
    return _safe(
        "Verified tenant knowledge for " + str(shown) + ": " + _field(row),
        blocked=False, evidence_status="EVIDENCE_AVAILABLE", plant_id=plant["plant_id"],
        plant_name=plant.get("name"), evidence=[row], count=1,
    )


def _summary_answer(text, rows, plant):
    low = text.lower()
    if not rows:
        return _safe(
            "The selected plant has no matching onboarded knowledge for that question yet. I will not use another plant's data.",
            blocked=True, reason="TENANT_KNOWLEDGE_NOT_FOUND", plant_id=plant["plant_id"], plant_name=plant.get("name"),
        )

    instrument_query = any(x in low for x in ("instrument", "pressure", "temperature", "flow", "level"))
    io_query = any(x in low for x in ("plc", "i/o", " io ", "input", "output"))
    categories = defaultdict(set)
    io = defaultdict(set)
    terms = _terms(text)
    scored = []
    for row in rows:
        hay = " ".join(str(row.get(k) or "") for k in ("external_id", "name", "area", "service", "asset_type", "tag", "source", "content")).lower()
        score = sum(term in hay for term in terms)
        scored.append((score, _richness(row), row))
        tag = _norm(row.get("tag") or row.get("external_id"))
        if tag:
            cat = _category(row)
            if cat: categories[cat].add(tag)
            io[_io_kind(row)].add(tag)
    scored.sort(key=lambda x: (-x[0], -x[1]))
    evidence = [x[2] for x in scored if _category(x[2])] if instrument_query else [x[2] for x in scored[:8]]
    evidence = evidence[:8]

    lines = [f"I found {len(rows)} matching knowledge record(s) in {plant.get('name', 'the selected plant')}, using only its onboarded data."]
    if instrument_query:
        for cat in ("Pressure", "Temperature", "Flow", "Level"):
            if categories[cat]: lines.append(f"{cat}: {len(categories[cat])} distinct indexed tag(s).")
    if io_query:
        for kind in ("DI", "DO", "AI", "AO", "Other"):
            if io[kind]: lines.append(f"{kind}: {len(io[kind])} distinct tag(s).")
    lines.append("Representative evidence:")
    for row in evidence:
        text_line = _field(row)
        if text_line: lines.append(text_line)
    sources = sorted({str(r.get("source")) for r in rows if r.get("source")})
    if sources:
        lines.append("Source documents: " + "; ".join(sources[:8]))
    return _safe("\n".join(lines), blocked=False, evidence_status="EVIDENCE_AVAILABLE",
                 plant_id=plant["plant_id"], plant_name=plant.get("name"), count=len(rows), evidence=evidence)


def _answer(text):
    plant_id, organization_id = _plant_context()
    if not plant_id:
        return _safe("No plant is selected. Select a plant before asking plant-specific questions.", blocked=True, reason="NO_ACTIVE_PLANT")
    plant = _plant(plant_id, organization_id)
    if not plant or str(plant.get("status", "")).upper() != "ACTIVE":
        return _safe("The selected plant context is invalid. I will not access plant data.", blocked=True, reason="INVALID_PLANT_CONTEXT")
    exact = _candidate(text)
    rows = _query_rows(plant_id, organization_id, identifier=exact, limit=80) if exact else _query_rows(plant_id, organization_id, terms=_terms(text), limit=120)
    if exact:
        return _exact_answer(text, rows, plant)
    return _summary_answer(text, rows, plant)


def install():
    try:
        import anvi_knowledge_layer as knowledge
    except Exception:
        return
    current = getattr(knowledge, "ask_anvi", None)
    if not callable(current) or getattr(current, "_anviqo_universal_engine", False):
        return

    def wrapped(q, *args, **kwargs):
        text = str(q or "").strip()
        if _is_data_question(text):
            try:
                return _answer(text)
            except Exception as exc:
                plant_id, _ = _plant_context()
                return _safe(
                    "ANVI could not complete that plant-knowledge query. No other plant's data was used. Please retry the same question.",
                    blocked=True, reason="TENANT_QUERY_ERROR", plant_id=plant_id, error_type=type(exc).__name__,
                )
        try:
            return current(q, *args, **kwargs)
        except Exception:
            plant_id, _ = _plant_context()
            return _safe("ANVI could not complete that request. No other plant's data was used.", blocked=True,
                         reason="QUERY_ERROR", plant_id=plant_id)

    wrapped._anviqo_universal_engine = True
    knowledge.ask_anvi = wrapped


__all__ = ["install"]
