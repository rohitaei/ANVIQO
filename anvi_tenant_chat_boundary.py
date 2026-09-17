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
    """Resolve chat plant from authenticated membership when session has no plant.

    Plant & User Management is provisioning/admin only. A single authorized
    active membership is safe to establish automatically. Multiple memberships
    remain fail-closed and require explicit plant context; no guessing/fallback.
    """
    try:
        from flask import session
        plant_id=session.get("plant_id")
        organization_id=session.get("organization_id")
        user_id=session.get("user_id")
        if plant_id:
            return plant_id,organization_id,"SESSION"
        if not user_id:
            return None,organization_id,"NO_AUTHENTICATED_USER"
        store=_tenant_store()
        if not store:
            return None,organization_id,"TENANT_STORE_UNAVAILABLE"
        p=store._placeholder()
        clauses=[f"m.user_id={p}","m.status='ACTIVE'","pl.status='ACTIVE'"]
        params=[user_id]
        if organization_id:
            clauses.append(f"m.organization_id={p}")
            params.append(organization_id)
        sql=("SELECT m.plant_id,m.organization_id,pl.name "
             "FROM anviqo_memberships m JOIN anviqo_plants pl ON pl.plant_id=m.plant_id "
             "WHERE "+" AND ".join(clauses)+" ORDER BY pl.name")
        with store._connect() as conn:
            cur=conn.cursor(); cur.execute(sql,tuple(params)); rows=cur.fetchall()
        if len(rows)==1:
            row=rows[0]
            if isinstance(row,dict):
                pid=row.get("plant_id"); oid=row.get("organization_id") or organization_id
            else:
                pid=row[0]; oid=row[1] or organization_id
            if pid:
                try:
                    session["plant_id"]=pid
                    if oid: session["organization_id"]=oid
                    session["plant_context_source"]="AUTHORIZED_MEMBERSHIP_SINGLE"
                except Exception:
                    pass
                return pid,oid,"AUTHORIZED_MEMBERSHIP_SINGLE"
        if len(rows)>1:
            return None,organization_id,"MULTIPLE_AUTHORIZED_PLANTS"
        return None,organization_id,"NO_AUTHORIZED_PLANT"
    except Exception:
        return None,None,"CONTEXT_RESOLUTION_ERROR"

def _prepare_tenant_db_url():
    url=os.getenv("ANVIQO_TENANT_DB_URL","").strip() or os.getenv("DATABASE_URL","").strip()
    if not url or url.startswith("sqlite:"): return
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
    if isinstance(row,dict): return dict(row)
    if hasattr(row,"keys"):
        try: return {k:row[k] for k in row.keys()}
        except Exception: pass
    if isinstance(row,(tuple,list)): return dict(zip(names,row))
    return {}

def _rows(plant_id, terms=None, tag=None, limit=2500):
    """Fetch only the selected tenant's relevant rows; avoid loading the full DB per chat turn."""
    store=_tenant_store()
    if not store or not plant_id: return []
    p=store._placeholder()
    fields="knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content,created_at"
    clauses=[f"plant_id={p}"]
    params=[plant_id]
    if tag:
        clauses.append(f"regexp_replace(upper(coalesce(tag,'')), '[^A-Z0-9]', '', 'g')={p}")
        params.append(_normalize(tag))
    elif terms:
        search=[]
        for term in list(dict.fromkeys(terms))[:10]:
            like=f"%{str(term).replace('%','')}%"
            search.append(" OR ".join(f"lower(coalesce({c},'')) LIKE {p}" for c in ("external_id","name","area","service","asset_type","tag","source","content")))
            params.extend([like]*8)
        if search: clauses.append("("+" OR ".join(search)+")")
    sql=f"SELECT {fields} FROM anviqo_plant_knowledge WHERE {' AND '.join(clauses)} ORDER BY created_at,knowledge_id LIMIT {int(limit)}"
    with store._connect() as conn:
        cur=conn.cursor(); cur.execute(sql,tuple(params)); raw=cur.fetchall()
    result=[]
    for raw_row in raw:
        item=_coerce_row(raw_row)
        meta=item.get("metadata")
        if isinstance(meta,str):
            try: item["metadata"]=json.loads(meta)
            except Exception: item["metadata"]={}
        result.append(item)
    return result

def _count_matches(plant_id, terms):
    store=_tenant_store()
    if not store or not plant_id or not terms: return 0
    p=store._placeholder(); clauses=[f"plant_id={p}"]; params=[plant_id]
    for term in list(dict.fromkeys(terms))[:10]:
        like=f"%{str(term).replace('%','')}%"
        clauses.append("("+" OR ".join(f"lower(coalesce({c},'')) LIKE {p}" for c in ("external_id","name","area","service","asset_type","tag","source","content"))+")")
        params.extend([like]*8)
    sql=f"SELECT count(*) FROM anviqo_plant_knowledge WHERE {' AND '.join(clauses)}"
    with store._connect() as conn:
        cur=conn.cursor(); cur.execute(sql,tuple(params)); row=cur.fetchone()
    return int(row[0] if not isinstance(row,dict) else next(iter(row.values()))) if row else 0

def _legacy(plant):
    return bool(plant and str(plant.get("slug","")).strip().lower()=="primary-plant")

def _safe_response(answer,**extra):
    payload={"answer":answer,**SAFETY}; payload.update(extra); return payload

_ENGINEERING_PREFIXES={"PT","TT","FT","LT","AT","DT","ST","WT","CT","TE","PE","FE","LE","AE","AI","AO","DI","DO","XV","FV","PV","TV","LV","ZV","ZS","ZSO","ZSC","PS","TS","LS","FS","AS","HS","CS","ES","IS","MS","SS","VB","PC","FC"}

def _candidate_tag(q):
    for token in re.findall(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b",q or ""):
        n=_normalize(token); m=re.match(r"[A-Z]+",n); prefix=m.group(0) if m else ""
        if prefix in _ENGINEERING_PREFIXES: return n
    return None

def _tag_from_question(q,rows=None):
    candidate=_candidate_tag(q)
    if candidate: return candidate
    known=set()
    for row in rows or []:
        row=_coerce_row(row)
        for key in ("tag","external_id"):
            if row.get(key): known.add(_normalize(row.get(key)))
    for token in re.findall(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b",q or ""):
        n=_normalize(token)
        if n in known: return n
    return None

def _question_terms(text):
    stop={"what","tell","me","about","do","you","have","the","for","and","to","in","of","is","are","available","information","this","that","plant","please","give","show","can","i","we","my","your","on","from","with","currently","selected","knowledge","including","their","documents"}
    terms=[]
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_./-]{1,}",str(text or "").lower()):
        if raw not in stop and len(_normalize(raw))>=2: terms.append(raw)
    return list(dict.fromkeys(terms))

def _metadata(row,key,*alts):
    meta=row.get("metadata") if isinstance(row.get("metadata"),dict) else {}
    for k in (key,)+alts:
        if meta.get(k) not in (None,""): return str(meta[k])
    return ""

def _io_kind(row):
    value=" ".join(str(row.get(k) or "") for k in ("record_type","asset_type","name","service","content"))
    value += " "+_metadata(row,"io_type","i_o_type")
    u=value.upper()
    for kind,patterns in (("DI",(" DI "," DIGITAL INPUT","DIGITAL INPUT","DIGITAL IN")),("DO",(" DO "," DIGITAL OUTPUT","DIGITAL OUTPUT","DIGITAL OUT")),("AI",(" AI "," ANALOG INPUT","4-20 MA","RTD","THERMOCOUPLE","TEMPERATURE INPUT")),("AO",(" AO "," ANALOG OUTPUT","ANALOG OUTPUT"))):
        padded=" "+re.sub(r"[^A-Z0-9-]+"," ",u)+" "
        if any(p in padded for p in patterns): return kind
    return "Other/unspecified"

def _instrument_category(row):
    text=" ".join(str(row.get(k) or "") for k in ("tag","name","service","asset_type","content")).upper()
    for category, words in (("Pressure",("PRESSURE"," PT")),("Temperature",("TEMPERATURE","TEMP","THERMOCOUPLE","RTD"," TT")),("Flow",("FLOW"," FT")),("Level",("LEVEL"," LT"))):
        if any(w in text for w in words): return category
    return None

def _field(row):
    vals=[]
    for key,label in (("tag","Tag"),("name","Instrument/service"),("area","Area"),("source","Source")):
        if row.get(key): vals.append(f"{label}: {row[key]}")
    for key,label in (("io_type","I/O"),("i_o_type","I/O"),("plc_address","PLC"),("panel","Panel"),("tb","TB"),("jb","JB"),("range","Range"),("unit","Unit"),("model","Model")):
        v=_metadata(row,key)
        if v: vals.append(f"{label}: {v}")
    return "; ".join(vals)

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
    top=[r for _,r in matches[:16]]
    low=text.lower()
    instrument_query=any(x in low for x in ("instrument","pressure","temperature","flow","level"))
    io_query=any(x in low for x in ("plc","i/o","io","input","output"))
    if instrument_query or io_query:
        categories={"Pressure":set(),"Temperature":set(),"Flow":set(),"Level":set()}
        io_counts={"DI":set(),"DO":set(),"AI":set(),"AO":set(),"Other/unspecified":set()}
        evidence=[]
        for _,r in matches:
            tag=str(r.get("tag") or r.get("external_id") or "").strip()
            if not tag: continue
            cat=_instrument_category(r)
            if cat: categories[cat].add(_normalize(tag))
            kind=_io_kind(r); io_counts[kind].add(_normalize(tag))
            if len(evidence)<10 and (cat or io_query): evidence.append(r)
        lines=[f"I found {len(matches)} matching knowledge record(s) in the selected plant {plant.get('name','UNKNOWN')}, using only its onboarded data."]
        if instrument_query:
            for cat in ("Pressure","Temperature","Flow","Level"):
                if categories[cat]: lines.append(f"{cat}: {len(categories[cat])} distinct indexed tag(s).")
        if io_query:
            lines.append("I/O coverage: "+", ".join(f"{k}: {len(v)} tag(s)" for k,v in io_counts.items() if v))
        lines.append("Representative evidence:")
        for r in evidence[:8]: lines.append(_field(r))
        lines.append("Source documents: "+", ".join(sorted({str(r.get('source')) for _,r in matches if r.get('source')})[:6]))
        return _safe_response("\n".join(lines),blocked=False,evidence_status="EVIDENCE_AVAILABLE",plant_id=plant["plant_id"],plant_name=plant.get("name"),count=len(matches),evidence=evidence[:8])
    top=top[:8]
    sources={}
    for _,r in matches:
        src=str(r.get("source") or "UNKNOWN"); sources[src]=sources.get(src,0)+1
    source_text="; ".join(f"{k}: {v} matching record(s)" for k,v in list(sources.items())[:6])
    lines=[f"I found {len(matches)} matching knowledge record(s) in the selected plant {plant.get('name','UNKNOWN')}, using only its onboarded data.",f"Sources: {source_text}.","Representative evidence:"]
    for r in top: lines.append(_field(r))
    return _safe_response("\n".join(lines),blocked=False,evidence_status="EVIDENCE_AVAILABLE",plant_id=plant["plant_id"],plant_name=plant.get("name"),count=len(matches),evidence=top)

def _tenant_answer(q,rows,plant):
    rows=[_coerce_row(r) for r in (rows or [])]
    text=str(q or "").strip(); low=text.lower()
    normalized_tags={_normalize(r.get("tag")):r for r in rows if r.get("tag")}
    if any(x in low for x in ("what plant","which plant","connected to","current plant","selected plant")):
        return _safe_response(f"ANVI is connected to {plant['name']} (selected plant).",plant_id=plant["plant_id"],plant_name=plant["name"])
    requested=_tag_from_question(text,rows)
    if requested:
        row=normalized_tags.get(requested)
        if not row: return _safe_response("I cannot find that tag in the currently selected plant's knowledge. I will not use another plant's data as a fallback.",blocked=True,reason="TENANT_KNOWLEDGE_NOT_FOUND",plant_id=plant["plant_id"],plant_name=plant["name"])
        fields={k:row.get(k) for k in ("tag","name","area","service","asset_type","record_type","external_id","parent_id","source")}
        meta=row.get("metadata")
        if isinstance(meta,dict):
            for key in ("io_type","i_o_type","plc_address","panel","tb","jb","criticality","model","range","unit"):
                if meta.get(key) is not None: fields[key]=meta[key]
        fields={k:v for k,v in fields.items() if v not in (None,"",[])}
        return _safe_response(f"Verified tenant knowledge for {row.get('tag') or row.get('name')}: "+", ".join(f"{k}: {v}" for k,v in fields.items() if k!="tag"),blocked=False,evidence_status="EVIDENCE_AVAILABLE",plant_id=plant["plant_id"],plant_name=plant["name"],evidence=[fields])
    if any(x in low for x in ("count","how many","number of")) and any(x in low for x in ("equipment","instrument","io","i/o","asset","device")):
        terms=_question_terms(text); count=_count_matches(plant["plant_id"],terms) if terms else 0
        return _safe_response(f"The selected plant {plant['name']} has {count} matching indexed equipment/instrument records in tenant knowledge.",blocked=False,evidence_status="EVIDENCE_AVAILABLE",plant_id=plant["plant_id"],plant_name=plant["name"],count=count)
    return _natural_knowledge_answer(text,rows,plant)

def _legacy_onboarding_question(q):
    low=str(q or "").lower()
    return any(term in low for term in ("mbf-2","mbf2","plc i/o","plc io","cable schedule","onboarded data","onboarding data","instrument","pressure","temperature","flow","level"))

def install():
    try:
        _prepare_tenant_db_url(); import anvi_knowledge_layer as knowledge
    except Exception: return
    original=getattr(knowledge,"ask_anvi",None)
    if not callable(original) or getattr(original,"_anviqo_tenant_boundary",False): return
    def wrapped(q,*args,**kwargs):
        plant_id,organization_id,context_source=_session_context()
        if not plant_id:
            if context_source=="MULTIPLE_AUTHORIZED_PLANTS":
                return _safe_response("Multiple authorized plants are available. Specify the plant context before asking a plant-specific question; ANVI will not guess or use another plant as a fallback.",blocked=True,reason="MULTIPLE_AUTHORIZED_PLANTS")
            return _safe_response("No authorized plant context is available for this user. ANVI will not access plant data.",blocked=True,reason="NO_AUTHORIZED_PLANT")
        plant=_plant(plant_id)
        if not plant or (organization_id and plant.get("organization_id")!=organization_id):
            return _safe_response("The authorized plant context is invalid. ANVI will not access plant data.",blocked=True,reason="INVALID_PLANT_CONTEXT")
        candidate=_candidate_tag(q)
        rows=_rows(plant_id,tag=candidate) if candidate else _rows(plant_id,terms=_question_terms(q))
        if _legacy(plant) and not _legacy_onboarding_question(q): return original(q,*args,**kwargs)
        result=_tenant_answer(q,rows,plant)
        if result is not None: return result
        if _legacy(plant): return original(q,*args,**kwargs)
        return _safe_response("I can only answer from this authorized plant's onboarded knowledge. That information is not available in this plant yet, so I will not use another plant's data as a fallback.",blocked=True,reason="TENANT_SCOPE_ONLY",plant_id=plant["plant_id"],plant_name=plant.get("name"))
    wrapped._anviqo_tenant_boundary=True
    knowledge.ask_anvi=wrapped

install()
