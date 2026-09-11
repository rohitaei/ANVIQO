"""Tenant-scoped universal plant ingestion runtime.

Adapter/indexing layer only. Frozen V5 intelligence and PLC/SCADA boundaries
are not modified. Principle: CHANGE DATA, NOT CODE.
"""
from __future__ import annotations
import csv, hashlib, io, json, re, threading, zipfile
from datetime import datetime, timezone
import anvi_tenant_store as store
from universal_onboarding import build_onboarding_package, SAFETY
INGESTION_VERSION="ANVIQO-PLANT-INGESTION-V1"
_JOB_LOCK=threading.Lock()
_JOBS={}
def _now(): return datetime.now(timezone.utc).isoformat()
def _p(): return store._placeholder()
def _actor():
 from flask import session
 return {"user_id":session.get("user_id",""),"organization_id":session.get("organization_id",""),"plant_id":session.get("plant_id",""),"role":session.get("role",""),"username":session.get("username","")}
def _admin():
 a=_actor(); return bool(a["user_id"] and a["organization_id"] and a["role"] in {"OWNER","ADMIN"})
def _plant_ok(plant_id, actor=None):
 a=actor or _actor()
 if not a["user_id"] or not a["organization_id"] or a["role"] not in {"OWNER","ADMIN"} or not plant_id: return False
 with store._connect() as conn:
  cur=conn.cursor(); cur.execute(f"SELECT 1 FROM anviqo_plants WHERE plant_id={_p()} AND organization_id={_p()} AND status='ACTIVE' LIMIT 1",(plant_id,a["organization_id"]))
  return cur.fetchone() is not None
def init_schema():
 if not store.enabled(): return
 with store._connect() as conn:
  cur=conn.cursor()
  if store._is_sqlite():
   cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_knowledge (knowledge_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, document_id TEXT, record_type TEXT NOT NULL, external_id TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT '', service TEXT NOT NULL DEFAULT '', asset_type TEXT NOT NULL DEFAULT '', tag TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', metadata TEXT NOT NULL DEFAULT '{}', content TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, UNIQUE(plant_id,external_id,source))")
   cur.execute("CREATE INDEX IF NOT EXISTS idx_anviqo_plant_knowledge_plant ON anviqo_plant_knowledge(plant_id)")
  else:
   cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_knowledge (knowledge_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), plant_id TEXT NOT NULL REFERENCES anviqo_plants(plant_id), document_id TEXT, record_type TEXT NOT NULL, external_id TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT '', service TEXT NOT NULL DEFAULT '', asset_type TEXT NOT NULL DEFAULT '', tag TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', metadata JSONB NOT NULL DEFAULT '{}'::jsonb, content TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(plant_id,external_id,source))")
   cur.execute("CREATE INDEX IF NOT EXISTS idx_anviqo_plant_knowledge_plant ON anviqo_plant_knowledge(plant_id)")
def _docx(raw):
 with zipfile.ZipFile(io.BytesIO(raw)) as z: xml=z.read("word/document.xml").decode("utf-8",errors="replace")
 return "\n".join(re.sub(r"<[^>]+>"," ",x).strip() for x in re.findall(r"<w:t[^>]*>(.*?)</w:t>",xml) if x.strip())
def _pdf(raw):
 try:
  from pypdf import PdfReader
  return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages)
 except Exception: return ""
def _xlsx(raw):
 try:
  from openpyxl import load_workbook
  wb=load_workbook(io.BytesIO(raw),read_only=True,data_only=True); out=[]
  try:
   for ws in wb.worksheets:
    rows=list(ws.iter_rows(values_only=True))
    if not rows: continue
    headers=[]
    for i,v in enumerate(rows[0]):
     h=str(v).strip() if v is not None else ""
     headers.append(h or f"column_{i+1}")
    # Treat a worksheet with a usable header row as structured plant data.
    # This preserves tags, areas, I/O addresses and other supplied fields
    # instead of flattening each row into an opaque text record.
    for idx,row in enumerate(rows[1:], start=2):
     vals=[v for v in row]
     if not any(v is not None and str(v).strip() for v in vals): continue
     rec={headers[i]: vals[i] for i in range(min(len(headers),len(vals)))}
     rec={str(k).strip(): v for k,v in rec.items() if str(k).strip()}
     rec["external_id"]=str(rec.get("external_id") or rec.get("id") or rec.get("tag") or rec.get("asset_id") or hashlib.sha256((ws.title+str(idx)+json.dumps(rec,sort_keys=True,default=str)).encode()).hexdigest()[:20])
     rec["source"]=ws.title
     rec["record_type"]=str(rec.get("record_type") or rec.get("entity_type") or rec.get("type") or "ASSET")
     out.append(rec)
    # If there was no usable data-row structure, retain the worksheet as a
    # document-like record rather than silently dropping the source.
    if len(out)==0 and any(v is not None and str(v).strip() for v in rows[0]):
     out.append({'external_id':hashlib.sha256((ws.title+"|"+"|".join(str(v) for v in rows[0] if v is not None)).encode()).hexdigest()[:20],'name':' | '.join(str(v).strip() for v in rows[0] if v is not None),'area':ws.title,'record_type':'TABULAR','source':ws.title})
  finally: wb.close()
  return out
 except Exception: return []
def _records(filename,raw):
 ext=filename.lower().rsplit('.',1)[-1] if '.' in filename else ''
 if ext=='csv':
  out=[]
  for i,row in enumerate(csv.DictReader(io.StringIO(raw.decode('utf-8-sig',errors='replace')))):
   row=dict(row); row['external_id']=str(row.get('external_id') or row.get('id') or row.get('tag') or row.get('asset_id') or hashlib.sha256((filename+str(i)+json.dumps(row,sort_keys=True)).encode()).hexdigest()[:20]); row['source']=filename; out.append(row)
  return out
 if ext=='json':
  data=json.loads(raw.decode('utf-8',errors='replace'))
  if isinstance(data,dict): data=data.get('records') or data.get('data') or [data]
  out=[]
  for i,row in enumerate(data if isinstance(data,list) else []):
   if not isinstance(row,dict): continue
   row=dict(row); row['external_id']=str(row.get('external_id') or row.get('id') or row.get('tag') or row.get('asset_id') or hashlib.sha256((filename+str(i)+json.dumps(row,sort_keys=True)).encode()).hexdigest()[:20]); row['source']=filename; out.append(row)
  return out
 if ext in {'xlsx','xls'}: return _xlsx(raw)
 text=_docx(raw) if ext=='docx' else _pdf(raw) if ext=='pdf' else raw.decode('utf-8',errors='replace') if ext in {'txt','log'} else ''
 if not text.strip(): return []
 return [{'external_id':hashlib.sha256((filename+str(i)).encode()).hexdigest()[:20],'name':filename,'record_type':'DOCUMENT','source':filename,'metadata':{'content':chunk}} for i,chunk in enumerate(text[i:i+6000] for i in range(0,len(text),6000))]
def ingest_plant(plant_id, actor=None):
 a=actor or _actor()
 if not _plant_ok(plant_id,a): raise PermissionError('OWNER/ADMIN access to this plant is required')
 init_schema(); p=_p()
 with store._connect() as conn:
  cur=conn.cursor(); cur.execute(f"SELECT p.name,o.industry FROM anviqo_plants p LEFT JOIN anviqo_plant_onboarding o ON o.plant_id=p.plant_id WHERE p.plant_id={p} AND p.organization_id={p}",(plant_id,a['organization_id'])); plant=cur.fetchone(); cur.execute(f"SELECT document_id,filename,content,sha256 FROM anviqo_plant_documents WHERE plant_id={p} AND organization_id={p} ORDER BY created_at",(plant_id,a['organization_id'])); docs=cur.fetchall()
 if not plant: raise ValueError('Plant not found')
 total=documents=0; errors=[]; rows=[]
 for document_id,filename,raw,digest in docs:
  try:
   records=_records(filename,bytes(raw)); identity={'organization_id':a['organization_id'],'plant_id':plant_id,'name':plant[0],'industry':plant[1] or ''}; package=build_onboarding_package(identity,records) if records else {'records':[]}
   for rec in package.get('records',[]):
    kid='know_'+hashlib.sha256((plant_id+document_id+rec['external_id']+rec.get('source','')).encode()).hexdigest()[:24]; meta=dict(rec.get('metadata') or {}); meta.update({'ingestion_version':INGESTION_VERSION,'document_sha256':digest}); content=str(meta.pop('content','') or '')
    rows.append((kid,a['organization_id'],plant_id,document_id,rec['record_type'],rec['external_id'],rec.get('name',''),rec.get('area',''),rec.get('service',''),rec.get('asset_type',''),rec.get('tag',''),rec.get('parent_id',''),rec.get('source',filename),json.dumps(meta),content)); total+=1
   documents+=1
  except Exception as exc: errors.append({'filename':filename,'error':str(exc)})
 if rows:
  with store._connect() as conn:
   cur=conn.cursor()
   if store._is_sqlite(): cur.executemany(f"INSERT OR REPLACE INTO anviqo_plant_knowledge(knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content,created_at) VALUES({','.join([p]*15)},{p})",[r+(_now(),) for r in rows])
   else: cur.executemany(f"INSERT INTO anviqo_plant_knowledge(knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content) VALUES({','.join([p]*15)}) ON CONFLICT(plant_id,external_id,source) DO UPDATE SET name=EXCLUDED.name,area=EXCLUDED.area,service=EXCLUDED.service,asset_type=EXCLUDED.asset_type,tag=EXCLUDED.tag,metadata=EXCLUDED.metadata,content=EXCLUDED.content",rows)
 status='READY' if documents and not errors else 'BLOCKED' if errors and not total else 'DATA_UPLOADED'
 with store._connect() as conn:
  cur=conn.cursor(); cur.execute(f"UPDATE anviqo_plant_onboarding SET status={p},updated_at={p} WHERE plant_id={p}",(status,_now(),plant_id))
 try: store.record_audit(a,'INGEST_PLANT_DATA','PLANT',plant_id,{'documents':documents,'records':total,'errors':len(errors)})
 except Exception: pass
 return {'status':'OK','plant_id':plant_id,'documents_processed':documents,'records_indexed':total,'errors':errors,'ingestion_version':INGESTION_VERSION,'safety':dict(SAFETY)}
def _run_job(plant_id, actor):
 try:
  result=ingest_plant(plant_id,actor); result['job_status']='COMPLETED'
 except Exception as exc:
  result={'status':'ERROR','plant_id':plant_id,'message':str(exc),'job_status':'FAILED','safety':dict(SAFETY)}
 with _JOB_LOCK: _JOBS[plant_id]=result
 try:
  p=_p(); status='READY' if result.get('status')=='OK' and not result.get('errors') else 'BLOCKED'
  with store._connect() as conn:
   cur=conn.cursor(); cur.execute(f"UPDATE anviqo_plant_onboarding SET status={p},updated_at={p} WHERE plant_id={p}",(status,_now(),plant_id))
 except Exception: pass
def register(app):
 from flask import jsonify,request
 @app.post('/api/admin/onboarding/plant/<plant_id>/ingest')
 def ingest_route(plant_id):
  actor=_actor()
  if not _plant_ok(plant_id,actor): return jsonify({'status':'FORBIDDEN','message':'OWNER/ADMIN access to this plant is required'}),403
  with _JOB_LOCK:
   existing=_JOBS.get(plant_id)
   if existing and existing.get('job_status')=='RUNNING': return jsonify({'status':'RUNNING','plant_id':plant_id,'message':'Universal ingestion is already running'}),202
   _JOBS[plant_id]={'status':'STARTED','plant_id':plant_id,'job_status':'RUNNING','message':'Universal ingestion started'}
  p=_p()
  try:
   with store._connect() as conn:
    cur=conn.cursor(); cur.execute(f"UPDATE anviqo_plant_onboarding SET status='INDEXING',updated_at={p} WHERE plant_id={p}",(_now(),plant_id))
  except Exception: pass
  threading.Thread(target=_run_job,args=(plant_id,actor),daemon=True,name=f'anvi-ingest-{plant_id}').start()
  return jsonify({'status':'STARTED','job_status':'RUNNING','plant_id':plant_id,'message':'Universal ingestion started. Monitor Onboarding Readiness for completion.','safety':dict(SAFETY)}),202
 @app.get('/api/admin/onboarding/plant/<plant_id>/ingest-status')
 def ingest_status_route(plant_id):
  actor=_actor()
  if not _plant_ok(plant_id,actor): return jsonify({'status':'FORBIDDEN'}),403
  with _JOB_LOCK: job=dict(_JOBS.get(plant_id) or {})
  return jsonify(job or {'status':'IDLE','job_status':'IDLE','plant_id':plant_id,'safety':dict(SAFETY)})
 @app.get('/api/plant/knowledge')
 def plant_knowledge_route():
  init_schema(); a=_actor(); plant_id=a.get('plant_id')
  if not a.get('user_id') or not plant_id: return jsonify({'status':'UNAUTHORIZED'}),401
  q=str(request.args.get('q','')).strip().lower(); limit=min(max(int(request.args.get('limit','50')),1),100)
  with store._connect() as conn:
   cur=conn.cursor(); sql=f"SELECT record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content FROM anviqo_plant_knowledge WHERE plant_id={_p()}"; args=[plant_id]
   if q: sql+=f" AND (LOWER(name) LIKE {_p()} OR LOWER(area) LIKE {_p()} OR LOWER(service) LIKE {_p()} OR LOWER(tag) LIKE {_p()} OR LOWER(content) LIKE {_p()})"; like=f'%{q}%'; args += [like]*5
   cur.execute(sql+' ORDER BY created_at DESC LIMIT '+str(limit),args); rows=cur.fetchall()
  out=[]
  for r in rows:
   meta=r[9]
   if isinstance(meta,str):
    try: meta=json.loads(meta)
    except Exception: meta={}
   out.append({'record_type':r[0],'external_id':r[1],'name':r[2],'area':r[3],'service':r[4],'asset_type':r[5],'tag':r[6],'parent_id':r[7],'source':r[8],'metadata':meta,'content':r[10]})
  return jsonify({'status':'OK','plant_id':plant_id,'count':len(out),'records':out,'safety':dict(SAFETY)})
 return app
__all__=['register','init_schema','ingest_plant']