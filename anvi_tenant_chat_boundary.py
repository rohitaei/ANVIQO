"""ANVIQO tenant chat boundary.

Presentation/routing layer only. V5 intelligence remains untouched. Selected
plant knowledge is fail-closed; no cross-tenant fallback and no PLC/SCADA write.
"""
from __future__ import annotations
import json
import os
import re

SAFETY={"tenant_scoped":True,"read_only":True,"plc_write":False,"scada_control":False,"human_decision_required":True}

def _normalize(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())

def _session_context():
    try:
        from flask import session
        return session.get("plant_id"), session.get("organization_id")
    except Exception:
        return None,None

def _prepare_tenant_db_url():
    url=os.getenv("ANVIQO_TENANT_DB_URL","").strip() or os.getenv("DATABASE_URL","").strip()
    if not url or url.startswith("sqlite:"):
        return
    if "sslmode=" not in url.lower():
        os.environ["ANVIQO_TENANT_DB_URL"]=url+("&" if "?" in url else "?")+"sslmode=require"

def _tenant_store():
    _prepare_tenant_db_url()
    try:
        import anvi_tenant_store as store
        if not store.enabled(): return None
        store.init_schema()
        return store
    except Exception:
        return None

def _plant(plant_id):
    store=_tenant_store()
    if not store or not plant_id: return None
    p=store._placeholder()
    with store._connect() as conn:
        cur=conn.cursor()
        cur.execute(f"SELECT plant_id,organization_id,name,slug,status FROM anviqo_plants WHERE plant_id={p}",(plant_id,))
        row=cur.fetchone()
    if not row: return None
    if isinstance(row,dict): return row
    return dict(zip(("plant_id","organization_id","name","slug","status"),row))

_KNOWLEDGE_NAMES=("knowledge_id","organization_id","plant_id","document_id","record_type","external_id","name","area","service","asset_type","tag","parent_id","source","metadata","content","created_at")

def _coerce_row(row, names=_KNOWLEDGE_NAMES):
    if isinstance(row,dict):
        return dict(row)
    if hasattr(row,"keys"):
        try: return {k:row[k] for k in row.keys()}
        except Exception: pass
    if isinstance(row,(tuple,list)):
        return dict(zip(names,row))
    return {}

def _rows(plant_id):
    store=_tenant_store()
    if not store or not plant_id: return []
    p=store._placeholder()
    with store._connect() as conn:
        cur=conn.cursor()
        cur.execute(f"SELECT knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content,created_at FROM anviqo_plant_knowledge WHERE plant_id={p} ORDER BY created_at,knowledge_id",(plant_id,))
        raw=cur.fetchall()
    result=[]
    for raw_row in raw:
        item=_coerce_row(raw_row)
        meta=item.get("metadata")
        if isinstance(meta,str):
            try: item["metadata"]=json.loads(meta)
            except Exception: item["metadata"]={}
        result.append(item)
    return result

def _legacy(plant):
    return bool(plant and str(plant.get("slug","")).strip().lower()=="primary-plant")

def _safe_response(answer,**extra):
    payload={"answer":answer,**SAFETY}
    payload.update(extra)
    return payload

_ENGINEERING_PREFIXES={"PT","TT","FT","LT","AT","DT","ST","WT","CT","TE","PE","FE","LE","AE","AI","AO","DI","DO","XV","FV","PV","TV","LV","ZV","ZS","ZSO","ZSC","PS","TS","LS","FS","AS","HS","CS","ES","IS","MS","SS","VB","PC","FC"}

def _tag_from_question(q,rows=None):
    known=set()
    for row in rows or []:
        row=_coerce_row(row)
        for key in ("tag","external_id"):
            if row.get(key): known.add(_normalize(row.get(key)))
    for token in re.findall(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b",q or ""):
        n=_normalize(token)
        if n in known: return n
        m=re.match(r"[A-Z]+",n); prefix=m.group(0) if m else ""
        if prefix in _ENGINEERING_PREFIXES: return n
    return None

def _question_terms(text):
    stop={"what","tell","me","about","do","you","have","the","for","and","to","in","of","is","are","available","information","this","that","plant","please","give","show","can","i","we","my","your","on","from","with","currently","selected","knowledge"}
    terms=[]
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_./-]{1,}",str(text or "").lower()):
        if raw not in stop and len(_normalize(raw))>=2: terms.append(raw)
    return list(dict.fromkeys(terms))

def _natural_knowledge_answer(text,rows,plant):
    terms=_question_terms(text)
    if not terms: return None
    matches=[]
    for raw_row in rows:
        row=_coerce_row(raw_row)
        hay=" ".join(str(row.get(k) or "") for k in ("external_id","name","area","service","asset_type","tag","source","content")).lower()
        score=sum(1 for term in terms if term in hay)
        if score: matches.append((score,row))
    if not matches: return None
    matches.sort(key=lambda x:(-x[0],str(x[1].get("knowledge_id") or "")))
    top=[r for _,r in matches[:12]]
    sources={}
    for _,r in matches:
        src=str(r.get("source") or "UNKNOWN"); sources[src]=sources.get(src,0)+1
    source_text="; ".join(f"{k}: {v} matching record(s)" for k,v in list(sources.items())[:6])
    lines=[f"I found {len(matches)} matching knowledge record(s) in the selected plant {plant.get('name','UNKNOWN')}, using only its onboarded data.",f"Sources: {source_text}.","Representative evidence:"]
    for r in top[:8]:
        label=r.get("tag") or r.get("external_id") or r.get("name") or "record"
        desc=r.get("name") or r.get("service") or r.get("record_type") or "knowledge record"
        lines.append(f"{label} — {desc}; Area: {r.get('area') or 'UNKNOWN'}; Source: {r.get('source') or 'UNKNOWN'}")
    return _safe_response("\n".join(lines),blocked=False,evidence_status="EVIDENCE_AVAILABLE",plant_id=plant["plant_id"],plant_name=plant.get("name"),count=len(matches),evidence=top[:8])

def _tenant_answer(q,rows,plant):
    rows=[_coerce_row(r) for r in (rows or [])]
    text=str(q or "").strip(); low=text.lower()
    normalized_tags={_normalize(r.get("tag")):r for r in rows if r.get("tag")}
    if any(x in low for x in ("what plant","which plant","connected to","current plant","selected plant")):
        return _safe_response(f"ANVI is connected to {plant['name']} (selected plant).",plant_id=plant["plant_id"],plant_name=plant["name"])
    requested=_tag_from_question(text,rows)
    if requested:
        row=normalized_tags.get(requested)
        if not row:
            return _safe_response("I cannot find that tag in the currently selected plant's knowledge. I will not use another plant's data as a fallback.",blocked=True,reason="TENANT_KNOWLEDGE_NOT_FOUND",plant_id=plant["plant_id"],plant_name=plant["name"])
        fields={k:row.get(k) for k in ("tag","name","area","service","asset_type","record_type","external_id","parent_id","source")}
        meta=row.get("metadata")
        if isinstance(meta,dict):
            for key in ("io_type","i_o_type","plc_address","panel","tb","criticality","model","range","unit"):
                if meta.get(key) is not None: fields[key]=meta[key]
        fields={k:v for k,v in fields.items() if v not in (None,"",[])}
        return _safe_response(f"Verified tenant knowledge for {row.get('tag') or row.get('name')}: "+", ".join(f"{k}: {v}" for k,v in fields.items() if k!="tag"),blocked=False,evidence_status="EVIDENCE_AVAILABLE",plant_id=plant["plant_id"],plant_name=plant["name"],evidence=[fields])
    if any(x in low for x in ("count","how many","number of")) and any(x in low for x in ("equipment","instrument","io","i/o","asset","device")):
        usable=[r for r in rows if r.get("tag") or str(r.get("record_type") or "").lower() in {"instrument","io","pci","asset"}]
        distinct={_normalize(r.get("tag")) or str(r.get("external_id") or r.get("knowledge_id")) for r in usable}; distinct.discard("")
        return _safe_response(f"The selected plant {plant['name']} has {len(distinct)} indexed equipment/instrument records in tenant knowledge.",blocked=False,evidence_status="EVIDENCE_AVAILABLE",plant_id=plant["plant_id"],plant_name=plant["name"],count=len(distinct))
    natural=_natural_knowledge_answer(text,rows,plant)
    if natural is not None: return natural
    if rows: return None
    return _safe_response(f"The selected plant {plant['name']} has no indexed onboarding knowledge yet. I will not use another plant's data as a fallback.",blocked=True,reason="TENANT_ONBOARDING_NOT_READY",plant_id=plant["plant_id"],plant_name=plant["name"])

def _legacy_onboarding_question(q):
    low=str(q or "").lower()
    return any(term in low for term in ("mbf-2","mbf2","plc i/o","plc io","cable schedule","onboarded data","onboarding data"))

def install():
    try:
        _prepare_tenant_db_url()
        import anvi_knowledge_layer as knowledge
    except Exception:
        return
    original=getattr(knowledge,"ask_anvi",None)
    if not callable(original) or getattr(original,"_anviqo_tenant_boundary",False): return
    def wrapped(q,*args,**kwargs):
        plant_id,organization_id=_session_context()
        if not plant_id: return _safe_response("No plant is selected. Select a plant before asking plant-specific questions.",blocked=True,reason="NO_ACTIVE_PLANT")
        plant=_plant(plant_id)
        if not plant or (organization_id and plant.get("organization_id")!=organization_id): return _safe_response("The selected plant context is invalid. I will not access plant data.",blocked=True,reason="INVALID_PLANT_CONTEXT")
        rows=_rows(plant_id)
        if _legacy(plant) and not _legacy_onboarding_question(q): return original(q,*args,**kwargs)
        result=_tenant_answer(q,rows,plant)
        if result is not None: return result
        if _legacy(plant): return original(q,*args,**kwargs)
        return _safe_response("I can only answer from the currently selected plant's onboarded knowledge. That information is not available in this plant yet, so I will not use another plant's data as a fallback.",blocked=True,reason="TENANT_SCOPE_ONLY",plant_id=plant["plant_id"],plant_name=plant.get("name"))
    wrapped._anviqo_tenant_boundary=True
    knowledge.ask_anvi=wrapped

install()
