"""V1.4 optimized universal tenant chat engine.

Read-only, tenant-scoped answer path. Designed to keep plant-data queries
bounded and predictable on Render PostgreSQL while preserving evidence-first
behavior and the existing V5/PCI safety boundary.
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

NAMES = ("knowledge_id","organization_id","plant_id","document_id","record_type","external_id","name","area","service","asset_type","tag","parent_id","source","metadata","content","created_at")
PREFIXES = ("PT","TT","FT","LT","AT","DT","ST","WT","CT","TE","PE","FE","LE","AE","AI","AO","DI","DO","XV","FV","PV","TV","LV","ZV","ZS","ZSO","ZSC","PS","TS","LS","FS","AS","HS","CS","ES","IS","MS","SS","VB","PC","FC","MFT")
STOP = {"what","tell","me","about","do","you","have","the","for","and","to","in","of","is","are","available","information","this","that","plant","please","give","show","can","i","we","my","your","on","from","with","currently","selected","knowledge","including","their","documents","details","instrument","instruments","source","sources","data"}


def _norm(v): return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


def _candidate(text):
    for token in re.findall(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b", str(text or "")):
        n = _norm(token)
        m = re.match(r"[A-Z]+", n)
        if m and m.group(0) in PREFIXES: return n
    return None


def _terms(text):
    out=[]
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_./-]{1,}", str(text or "").lower()):
        if raw not in STOP and len(_norm(raw)) >= 2: out.append(raw)
    return list(dict.fromkeys(out))[:10]


def _store():
    try:
        import anvi_tenant_store as store
        url=os.getenv("ANVIQO_TENANT_DB_URL","").strip() or os.getenv("DATABASE_URL","").strip()
        if url and not url.startswith("sqlite:") and "sslmode=" not in url.lower():
            os.environ["ANVIQO_TENANT_DB_URL"]=url+("&" if "?" in url else "?")+"sslmode=require"
        return store if store.enabled() else None
    except Exception:
        return None


def _row(row):
    if isinstance(row,dict): item=dict(row)
    elif hasattr(row,"keys"):
        try: item={k:row[k] for k in row.keys()}
        except Exception: item={}
    elif isinstance(row,(tuple,list)): item=dict(zip(NAMES,row))
    else: item={}
    if isinstance(item.get("metadata"),str):
        try: item["metadata"]=json.loads(item["metadata"])
        except Exception: item["metadata"]={}
    return item


def _safe(answer,**extra):
    p={"answer":answer,**SAFETY}; p.update(extra); return p


def _meta_value(meta, *aliases):
    if not isinstance(meta, dict):
        return ""
    wanted={re.sub(r"[^a-z0-9]+","",str(k).lower()) for k in aliases}
    for key,value in meta.items():
        if re.sub(r"[^a-z0-9]+","",str(key).lower()) in wanted and value not in (None,""):
            return str(value).strip()
    return ""

def _field(row):
    row=_row(row); meta=row.get("metadata") if isinstance(row.get("metadata"),dict) else {}; vals=[]
    for k,l in (("tag","Tag"),("external_id","External ID"),("name","Instrument/service"),("area","Area"),("source","Source")):
        if row.get(k): vals.append(f"{l}: {row[k]}")
    fields=(
        (("io_type","i_o_type","I/O TYPE","signal type"),"I/O"),
        (("plc_address","PLC ADDRESS","address"),"PLC"),
        (("panel","PANEL","panel name"),"Panel"),
        (("tb","tb_name","TB NAME","TB NO","TB NUMBER","terminal block"),"TB"),
        (("tb_no","TB NO","TB NUMBER"),"TB No"),
        (("jb","jb_name","JB NAME","JB NO","JB NUMBER","junction box"),"JB"),
        (("jb_no","JB NO","JB NUMBER"),"JB No"),
        (("range","instrument range","measurement range"),"Range"),
        (("unit","engineering unit","engg unit"),"Unit"),
        (("model","model no","model number"),"Model"),
        (("criticality","critical"),"Criticality"),
        (("description","service description","instrument description"),"Description"),
    )
    for aliases,label in fields:
        value=_meta_value(meta,*aliases)
        if value: vals.append(f"{label}: {value}")
    return "; ".join(vals)

def _richness(row):
    row=_row(row); meta=row.get("metadata") if isinstance(row.get("metadata"),dict) else {}
    meta_fields=("io_type","i_o_type","plc_address","panel","tb","tb_name","tb_no","jb","jb_name","jb_no","range","unit","model","criticality","description")
    return sum(bool(str(row.get(k) or "").strip()) for k in ("tag","external_id","name","area","service","asset_type","record_type","source","content"))+sum(bool(_meta_value(meta,k)) for k in meta_fields)

def _execute(sql,params):
    store=_store()
    if not store: raise RuntimeError("TENANT_STORE_UNAVAILABLE")
    with store._connect() as conn:
        cur=conn.cursor()
        try: cur.execute("SET LOCAL statement_timeout = '3000ms'")
        except Exception: pass
        try: cur.execute("SET LOCAL lock_timeout = '500ms'")
        except Exception: pass
        cur.execute(sql,tuple(params))
        return [_row(r) for r in cur.fetchall()]


def _query_rows(plant_id,organization_id,identifier=None,terms=None,limit=120):
    store=_store()
    if not store or not plant_id: raise RuntimeError("TENANT_STORE_UNAVAILABLE")
    p=store._placeholder(); fields=",".join(NAMES); clauses=[f"plant_id={p}"]; params=[plant_id]
    if organization_id: clauses.append(f"organization_id={p}"); params.append(organization_id)
    if identifier:
        n=_norm(identifier)
        exact=" OR ".join(f"regexp_replace(upper(coalesce({c},'')), '[^A-Z0-9]', '', 'g')={p}" for c in ("tag","external_id","name","service"))
        sql=f"SELECT {fields} FROM anviqo_plant_knowledge WHERE {' AND '.join(clauses)} AND ({exact}) ORDER BY created_at DESC LIMIT {min(int(limit),80)}"
        rows=_execute(sql,params+[n]*4)
        if rows: return rows
        # Search preserved source metadata too; real engineering sheets often use
        # non-canonical headers such as Instrument Tag or Loop Tag.
        sql=f"SELECT {fields} FROM anviqo_plant_knowledge WHERE {' AND '.join(clauses)} AND (regexp_replace(upper(coalesce(content,'')), '[^A-Z0-9]', '', 'g') LIKE {p} OR regexp_replace(upper(coalesce(metadata::text,'')), '[^A-Z0-9]', '', 'g') LIKE {p}) ORDER BY created_at DESC LIMIT {min(int(limit),40)}"
        return _execute(sql,params+[f"%{n}%",f"%{n}%"])
    terms=list(terms or [])[:10]
    if not terms: return []
    searchable=("external_id","name","area","service","asset_type","tag","source","content")
    category={"pressure","temperature","temp","flow","level","instrument","instruments"}
    context=[t for t in terms if t not in category]; wanted=[t for t in terms if t in category]
    for term in context:
        like=f"%{str(term).replace('%','')}%"
        clauses.append("("+" OR ".join(f"lower(coalesce({c},'')) LIKE {p}" for c in searchable)+")")
        params.extend([like]*len(searchable))
    if wanted:
        groups=[]
        for term in wanted:
            like=f"%{str(term).replace('%','')}%"; groups.append("("+" OR ".join(f"lower(coalesce({c},'')) LIKE {p}" for c in ("name","service","asset_type","tag","content"))+")"); params.extend([like]*5)
        clauses.append("("+" OR ".join(groups)+")")
    sql=f"SELECT {fields} FROM anviqo_plant_knowledge WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT {min(int(limit),120)}"
    return _execute(sql,params)


def _pci_resolve_rows(plant_id, organization_id, query):
    """Resolve a universal engineering identifier with the frozen PCI resolver.

    The resolver algorithm is unchanged. Only the tenant's imported rows are
    supplied to it. After identity resolution, related rows for the same
    normalized tag are folded into one evidence record so engineering
    attributes split across PLC/I-O/cable sheets are presented together.
    """
    store=_store()
    if not store or not plant_id: return []
    p=store._placeholder(); fields=",".join(NAMES)
    clauses=[f"plant_id={p}"]; params=[plant_id]
    if organization_id:
        clauses.append(f"organization_id={p}"); params.append(organization_id)
    rows=_execute(
        f"SELECT {fields} FROM anviqo_plant_knowledge "
        f"WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT 5000",
        params,
    )
    if not rows: return []
    try:
        from pci_universal_resolver import resolve
    except Exception:
        return []

    def meta_map(row):
        meta=row.get("metadata") if isinstance(row.get("metadata"),dict) else {}
        return {re.sub(r"[^a-z0-9]+","",str(k).lower()):v for k,v in meta.items() if v not in (None,"")}

    def value(row,*keys):
        meta=meta_map(row)
        wanted={re.sub(r"[^a-z0-9]+","",str(k).lower()) for k in keys}
        for key in wanted:
            if meta.get(key) not in (None,""):
                return meta[key]
        return ""

    def row_tag(row):
        return str(row.get("tag") or value(row,"plc_tag","instrument_tag","loop_tag","tag_name","tag") or "").strip()

    records=[]
    for row in rows:
        tag=row_tag(row)
        desc=row.get("name") or row.get("service") or value(row,"description","instrument_description","service_description") or row.get("content") or ""
        records.append({
            "tag":str(tag),
            "fox_plc_tag":str(value(row,"plc_tag","fox_plc_tag")),
            "description":str(desc),
            "io_type":str(value(row,"io_type","i_o_type")),
            "plc_address":str(value(row,"plc_address")),
            "panel":str(value(row,"panel")),
            "tb_name":str(value(row,"tb","tb_name")),
            "tb_no":str(value(row,"tb_no")),
            "jb_name":str(value(row,"jb","jb_name")),
            "jb_no":str(value(row,"jb_no")),
            "source_sheet":str(row.get("source") or ""),
            "_universal_row":row,
        })

    resolved,_match=resolve(query,records)
    if not resolved: return []

    # Fold all imported evidence rows belonging to the resolved identifier.
    # This is data aggregation only; no new reasoning or plant-specific rules.
    out=[]
    seen=set()
    for hit in resolved:
        base=hit.get("_universal_row") or {}
        wanted=row_tag(base)
        if not wanted:
            wanted=str(hit.get("tag") or "")
        wanted_norm=re.sub(r"[^A-Z0-9]+","",wanted.upper())
        related=[]
        for row in rows:
            rt=row_tag(row)
            rn=re.sub(r"[^A-Z0-9]+","",rt.upper())
            if rn and wanted_norm and rn==wanted_norm:
                related.append(row)
        if not related:
            related=[base]

        merged=dict(base)
        merged_meta=dict(base.get("metadata") or {}) if isinstance(base.get("metadata"),dict) else {}
        for row in related:
            for key in ("tag","external_id","name","area","service","asset_type","parent_id","source","content"):
                if not merged.get(key) and row.get(key):
                    merged[key]=row.get(key)
            meta=row.get("metadata") if isinstance(row.get("metadata"),dict) else {}
            for key,val in meta.items():
                if val not in (None,"") and (key not in merged_meta or merged_meta.get(key) in (None,"")):
                    merged_meta[key]=val
        merged["metadata"]=merged_meta
        identity=re.sub(r"[^A-Z0-9]+","",str(merged.get("tag") or merged.get("external_id") or "").upper())
        if identity and identity not in seen:
            out.append(merged); seen.add(identity)
    return out


def _plant_context():
    try:
        from flask import session
        return session.get("plant_id"),session.get("organization_id")
    except Exception: return None,None


def _repair_single_plant_context(plant_id, organization_id):
    if not organization_id:
        return None
    store=_store()
    if not store:
        return None
    try:
        p=store._placeholder()
        with store._connect() as conn:
            cur=conn.cursor()
            cur.execute(
                f"""SELECT m.plant_id,p.name,p.slug
                    FROM anviqo_memberships m
                    JOIN anviqo_plants p ON p.plant_id=m.plant_id
                    WHERE m.user_id={p}
                      AND m.organization_id={p}
                      AND m.status='ACTIVE'
                      AND p.status='ACTIVE'
                    ORDER BY p.name""",
                (__import__('flask').session.get("user_id",""), organization_id),
            )
            rows=cur.fetchall()
        if len(rows)!=1:
            return None
        repaired_id=rows[0][0]
        if repaired_id==plant_id:
            return repaired_id
        from flask import session
        session["plant_id"]=repaired_id
        session["plant_name"]=rows[0][1]
        session["plant_slug"]=rows[0][2]
        session.modified=True
        return repaired_id
    except Exception:
        return None


def _plant(plant_id,organization_id):
    """Validate the plant identity independently of optional org metadata.

    The membership resolver has already authorized (plant_id, organization_id)
    against the ACTIVE membership + ACTIVE plant join. Requiring the plant row
    to repeat the membership's organization_id here caused valid memberships
    to fail when the plant's organization metadata differed or was NULL.
    """
    store=_store()
    if not store or not plant_id: return None
    p=store._placeholder()
    sql=f"SELECT plant_id,organization_id,name,slug,status FROM anviqo_plants WHERE plant_id={p} LIMIT 1"
    rows=_execute(sql,[plant_id])
    return rows[0] if rows else None


def _category(row):
    text=" ".join(str(row.get(k) or "") for k in ("tag","name","service","asset_type","content")).upper()
    if "PRESSURE" in text or re.search(r"\bPT[_ -]?\d",text): return "Pressure"
    if any(x in text for x in ("TEMPERATURE","TEMP","THERMOCOUPLE","RTD")) or re.search(r"\bTT[_ -]?\d",text): return "Temperature"
    if "FLOW" in text or re.search(r"\bFT[_ -]?\d",text): return "Flow"
    if "LEVEL" in text or re.search(r"\bLT[_ -]?\d",text): return "Level"
    return None


def _io_kind(row):
    meta=row.get("metadata") if isinstance(row.get("metadata"),dict) else {}; v=" ".join(str(row.get(k) or "") for k in ("record_type","asset_type","name","service","content"))+" "+str(meta.get("io_type") or meta.get("i_o_type") or "")
    u=" "+re.sub(r"[^A-Z0-9-]+"," ",v.upper())+" "
    if " DIGITAL INPUT " in u or " DI " in u:return "DI"
    if " DIGITAL OUTPUT " in u or " DO " in u:return "DO"
    if " ANALOG OUTPUT " in u or " AO " in u:return "AO"
    if " ANALOG INPUT " in u or " AI " in u or "4-20 MA" in u or " RTD " in u:return "AI"
    return "Other"


def _exact_answer(text,rows,plant):
    requested=_candidate(text)
    if not requested:return None
    exact=[r for r in rows if any(_norm(r.get(k))==requested for k in ("tag","external_id","name","service"))]
    if not exact: exact=[r for r in rows if requested in _norm(r.get("content"))]
    if not exact:
        exact=[r for r in rows if requested in _norm(json.dumps(r.get("metadata") or {}, ensure_ascii=False))]
    if not exact:return _safe("I cannot find that tag in the currently selected plant's knowledge. I will not use another plant's data as a fallback.",blocked=True,reason="TENANT_KNOWLEDGE_NOT_FOUND",plant_id=plant["plant_id"],plant_name=plant.get("name"))
    row=max(exact,key=_richness); shown=row.get("tag") or row.get("external_id") or requested
    return _safe("Verified tenant knowledge for "+str(shown)+": "+_field(row),blocked=False,evidence_status="EVIDENCE_AVAILABLE",plant_id=plant["plant_id"],plant_name=plant.get("name"),evidence=[row],count=1)


def _summary_answer(text,rows,plant):
    if not rows:return _safe("The selected plant has no matching onboarded knowledge for that question yet. I will not use another plant's data.",blocked=True,reason="TENANT_KNOWLEDGE_NOT_FOUND",plant_id=plant["plant_id"],plant_name=plant.get("name"))
    low=text.lower(); instrument=any(x in low for x in ("instrument","pressure","temperature","flow","level")); ioq=any(x in low for x in ("plc","i/o"," io ","input","output")); terms=_terms(text); cats=defaultdict(set); ios=defaultdict(set); scored=[]
    for r in rows:
        hay=" ".join(str(r.get(k) or "") for k in ("external_id","name","area","service","asset_type","tag","source","content")).lower(); scored.append((sum(t in hay for t in terms),_richness(r),r)); tag=_norm(r.get("tag") or r.get("external_id"));
        if tag:
            c=_category(r)
            if c: cats[c].add(tag)
            ios[_io_kind(r)].add(tag)
    scored.sort(key=lambda x:(-x[0],-x[1])); evidence=[x[2] for x in scored if _category(x[2])] if instrument else [x[2] for x in scored[:8]]; evidence=evidence[:8]
    lines=[f"I found {len(rows)} matching knowledge record(s) in {plant.get('name','the selected plant')}, using only its onboarded data."]
    if instrument:
        for c in ("Pressure","Temperature","Flow","Level"):
            if cats[c]:lines.append(f"{c}: {len(cats[c])} distinct indexed tag(s).")
    if ioq:
        for k in ("DI","DO","AI","AO","Other"):
            if ios[k]:lines.append(f"{k}: {len(ios[k])} distinct tag(s).")
    lines.append("Representative evidence:")
    for r in evidence:
        s=_field(r)
        if s:lines.append(s)
    src=sorted({str(r.get("source")) for r in rows if r.get("source")})
    if src:lines.append("Source documents: "+"; ".join(src[:8]))
    return _safe("\n".join(lines),blocked=False,evidence_status="EVIDENCE_AVAILABLE",plant_id=plant["plant_id"],plant_name=plant.get("name"),count=len(rows),evidence=evidence)


def _answer(text):
    # Resolve the authenticated membership HERE, in the actual universal
    # answer function. Do not depend on a UI plant selector or a stale
    # session plant_id. This is the single source of truth for V1.4 chat.
    try:
        import anvi_tenant_context_autofix as _context_fix
        pid, oid, context_source = _context_fix.resolve()
    except Exception as exc:
        return _safe("ANVI could not establish the authenticated plant context. No other plant's data was used.",blocked=True,reason="TENANT_CONTEXT_ERROR",error_type=type(exc).__name__)

    if not pid:
        if context_source == "MULTIPLE_AUTHORIZED_PLANTS":
            return _safe("Multiple authorized plants are available for this account. ANVI requires an explicit plant context and will not guess or use another plant.",blocked=True,reason="MULTIPLE_AUTHORIZED_PLANTS")
        if context_source == "NO_AUTHENTICATED_USER":
            return _safe("ANVI requires an authenticated user before answering plant-specific questions.",blocked=True,reason="NO_AUTHENTICATED_USER")
        return _safe("No active authorized plant is available for this account. ANVI will not use another plant's data as a fallback.",blocked=True,reason="NO_AUTHORIZED_PLANT")

    plant=_plant(pid,oid)
    if not plant or str(plant.get("status","")).upper()!="ACTIVE":
        return _safe("The authenticated plant membership is not active or the plant record is unavailable. ANVI will not use another plant's data as a fallback.",blocked=True,reason="INVALID_PLANT_CONTEXT",plant_id=pid)
    candidate=_candidate(text)
    if candidate:
        # PCI resolver is the primary identity engine. If it cannot map a
        # universal engineering row, fall back to the same tenant-scoped
        # evidence index used by the importer. This preserves the PCI
        # resolver while allowing arbitrary spreadsheet tag columns.
        rows=_pci_resolve_rows(pid,oid,candidate)
        if not rows:
            rows=_query_rows(pid,oid,identifier=candidate,limit=80)
    else:
        rows=_query_rows(pid,oid,terms=_terms(text),limit=80)
    return _exact_answer(text,rows,plant) if candidate else _summary_answer(text,rows,plant)


def _is_data_question(text):
    low=str(text or "").lower()
    return bool(_candidate(text) or any(x in low for x in ("instrument","pressure","temperature","flow","level","plc","i/o"," io ","equipment","tag","panel","terminal","tb","jb","cable","source document","onboard","knowledge","plant data","maintenance","spare","alarm","event","plant health","health","shift report","report")))


def install():
    try: import anvi_knowledge_layer as knowledge
    except Exception:return
    current=getattr(knowledge,"ask_anvi",None)
    if not callable(current) or getattr(current,"_anviqo_universal_engine",False):return
    def wrapped(q,*args,**kwargs):
        text=str(q or "").strip()
        if _is_data_question(text):
            try:return _answer(text)
            except Exception as exc:
                pid,_=_plant_context(); return _safe("ANVI could not complete that plant-knowledge query. No other plant's data was used. Please retry the same question.",blocked=True,reason="TENANT_QUERY_ERROR",plant_id=pid,error_type=type(exc).__name__)
        try:return current(q,*args,**kwargs)
        except Exception:
            pid,_=_plant_context(); return _safe("ANVI could not complete that request. No other plant's data was used.",blocked=True,reason="QUERY_ERROR",plant_id=pid)
    wrapped._anviqo_universal_engine=True; knowledge.ask_anvi=wrapped

__all__=["install","_query_rows","_exact_answer","_summary_answer"]
