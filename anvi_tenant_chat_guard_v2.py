"""Strict selected-plant conversational boundary for ANVIQO."""
from __future__ import annotations
import json, re

SAFETY={"read_only":True,"plc_write":False,"scada_control":False,"human_decision_required":True,"automatic_authorization":False,"automatic_execution":False}
TAG_RE=re.compile(r"\b(?:PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|CV|FV|XV|MCV|FSV|PCV|SOV|AI|AO|DI|DO)[-_]?\d+[A-Z0-9_-]*\b",re.I)

def active_plant():
    try:
        from flask import has_request_context,session
        return str(session.get("plant_id") or "").strip() if has_request_context() else ""
    except Exception:return ""

def rows(plant_id):
    if not plant_id:return []
    try:
        import anvi_plant_ingestion_runtime as ingestion
        import anvi_tenant_store as store
        ingestion.init_schema(); p=store._placeholder()
        with store._connect() as conn:
            cur=conn.cursor(); cur.execute(f"SELECT record_type,external_id,name,area,service,asset_type,tag,source,metadata,content FROM anviqo_plant_knowledge WHERE plant_id={p}",(plant_id,)); data=cur.fetchall()
        out=[]
        for r in data:
            meta=r[8]
            if isinstance(meta,str):
                try:meta=json.loads(meta)
                except Exception:meta={}
            out.append({"record_type":str(r[0] or ""),"external_id":str(r[1] or ""),"name":str(r[2] or ""),"area":str(r[3] or ""),"service":str(r[4] or ""),"asset_type":str(r[5] or ""),"tag":str(r[6] or ""),"source":str(r[7] or ""),"metadata":meta if isinstance(meta,dict) else {},"content":str(r[9] or "")})
        return out
    except Exception:return []

def norm(x):return re.sub(r"[^A-Z0-9]","",str(x or "").upper())

def other_plant(q,pid):
    try:
        import anvi_tenant_store as store
        with store._connect() as conn:
            cur=conn.cursor();cur.execute("SELECT plant_id,name,slug FROM anviqo_plants WHERE status='ACTIVE'")
            ql=q.lower()
            for oid,name,slug in cur.fetchall():
                if str(oid)==pid:continue
                for v in (name,slug):
                    v=str(v or "").strip()
                    if v and len(v)>=3 and re.search(r"(?<![a-z0-9])"+re.escape(v.lower())+r"(?![a-z0-9])",ql):return v
    except Exception:pass
    return ""

def answer(q,rs):
    pid=active_plant(); ql=" "+str(q or "").lower()+" "; tags=[norm(x) for x in TAG_RE.findall(q)]
    if other_plant(q,pid):
        return {"answer":"I can only answer from the currently selected plant. The requested plant is outside this active plant context, so I will not disclose its data.","domain":"tenant_isolation","blocked":True,"tenant_isolation":True,**SAFETY}
    prs=[r for r in rs if r.get("tag") or r.get("record_type","").lower() in ("instrument","io","pci")]
    if not prs:return None
    if tags:
        m=[r for r in prs if norm(r.get("tag")) in tags or norm(r.get("external_id")) in tags]
        if not m:return {"answer":"I cannot find that instrument/equipment in the currently selected plant's knowledge. I will not use another plant's data as a fallback.","domain":"tenant_isolation","blocked":True,"tenant_isolation":True,**SAFETY}
        return {"answer":"\n".join([f"ANVI found {len(m)} record(s) in the selected plant:"]+[f"{r.get('tag') or r.get('external_id')} — {r.get('name') or 'No description'}; Area: {r.get('area') or 'UNKNOWN'}; Source: {r.get('source') or 'UNKNOWN'}" for r in m[:20]]),"domain":"pci","records":m[:20],"count":len(m),"tenant_isolation":True,**SAFETY}
    if any(x in ql for x in ("how many","count","total","number of","show all","list all","which instruments","which i/o","which io")) and any(x in ql for x in ("pci","instrument","i/o"," io ","plc","transmitter","tag")):
        return {"answer":f"The selected plant has {len(prs)} tenant-scoped knowledge record(s). I will not use another plant's data for this request.","domain":"pci","count":len(prs),"records":[],"tenant_isolation":True,**SAFETY}
    return None

def install():
    try:
        import anvi_knowledge_layer as layer
        original=getattr(layer,"ask_anvi",None)
        if not callable(original) or getattr(original,"_anviqo_strict_tenant",False):return False
        def wrapped(q,*a,**kw):
            pid=active_plant()
            if pid:
                rs=rows(pid)
                if rs:
                    r=answer(q,rs)
                    if r is not None:return r
            return original(q,*a,**kw)
        wrapped._anviqo_strict_tenant=True
        layer.ask_anvi=wrapped
        return True
    except Exception:return False
