"""Tenant-scoped universal plant ingestion runtime.

Adapter/indexing layer only. Frozen V5 intelligence and PLC/SCADA boundaries
are not modified. Principle: CHANGE DATA, NOT CODE.
"""
from __future__ import annotations
import csv, hashlib, io, json, re, zipfile
from datetime import datetime, timezone
import anvi_tenant_store as store
from universal_onboarding import build_onboarding_package, SAFETY
INGESTION_VERSION="ANVIQO-PLANT-INGESTION-V1"
def _now(): return datetime.now(timezone.utc).isoformat()
def _p(): return store._placeholder()
def _actor():
 from flask import session
 return {"user_id":session.get("user_id",""),"organization_id":session.get("organization_id",""),"plant_id":session.get("plant_id",""),"role":session.get("role",""),"username":session.get("username","")}
def _admin():
 a=_actor(); return bool(a["user_id"] and a["organization_id"] and a["role"] in {"OWNER","ADMIN"})
def _plant_ok(plant_id):
 a=_actor()
 if not _admin() or not plant_id: return False
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
  for ws in wb.worksheets:
   for row in ws.iter_rows(values_only=True):
    vals=[str(v).strip() for v in row if v is not None and str(v).strip()]
    if vals: out.append((ws.title,vals))
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
 if ext in {'xlsx','xls'}: return [{'external_id':hashlib.sha256((filename+s+'|'.join(v)).encode()).hexdigest()[:20],'name':' | '.join(v),'area':s,'record_type':'TABULAR','source':filename} for s,v in _xlsx(raw)]
 text=_docx(raw) if ext=='docx' else _pdf(raw) if ext=='pdf' else raw.decode('utf-8',errors='replace') if ext in {'txt','log'} else ''
 if not text.strip(): return []
 return [{'external_id':hashlib.sha256((filename+str(i)).encode()).hexdigest()[:20],'name':filename,'record_type':'DOCUMENT','source':filename,'metadata':{'content':chunk}} for i,chunk in enumerate(text[i:i+6000] for i in range(0,len(text),6000))]
def ingest_plant(plant_id):
 if not _plant_ok(plant_id): raise PermissionError('OWNER/ADMIN access to this plant is required')
 init_schema(); a=_actor(); p=_p()
 with store._connect() as conn:
  cur=conn.cursor(); cur.execute(f"SELECT p.name,o.industry FROM anviqo_plants p LEFT JOIN anviqo_plant_onboarding o ON o.plant_id=p.plant_id WHERE p.plant_id={p} AND p.organization_id={p}",(plant_id,a['organization_id'])); plant=cur.fetchone(); cur.execute(f"SELECT document_id,filename,content,sha256 FROM anviqo_plant_documents WHERE plant_id={p} AND organization_id={p} ORDER BY created_at",(plant_id,a['organization_id'])); docs=cur.fetchall()
 if not plant: raise ValueError('Plant not found')
 total=documents=0; errors=[]
 with store._connect() as conn:
  cur=conn.cursor()
  for document_id,filename,raw,digest in docs:
   try:
    records=_records(filename,bytes(raw)); identity={'organization_id':a['organization_id'],'plant_id':plant_id,'name':plant[0],'industry':plant[1] or ''}; package=build_onboarding_package(identity,records) if records else {'records':[]}
    for rec in package.get('records',[]):
     kid='know_'+hashlib.sha256((plant_id+document_id+rec['external_id']+rec.get('source','')).encode()).hexdigest()[:24]; meta=dict(rec.get('metadata') or {}); meta.update({'ingestion_version':INGESTION_VERSION,'document_sha256':digest}); content=str(meta.pop('content','') or '')
     vals=(kid,a['organization_id'],plant_id,document_id,rec['record_type'],rec['external_id'],rec.get('name',''),rec.get('area',''),rec.get('service',''),rec.get('asset_type',''),rec.get('tag',''),rec.get('parent_id',''),rec.get('source',filename),json.dumps(meta),content)
     if store._is_sqlite(): cur.execute(f"INSERT OR REPLACE INTO anviqo_plant_knowledge(knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content,created_at) VALUES({','.join([p]*15)},{p})",vals+(_now(),))
     else: cur.execute(f"INSERT INTO anviqo_plant_knowledge(knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content) VALUES({','.join([p]*15)}) ON CONFLICT(plant_id,external_id,source) DO UPDATE SET name=EXCLUDED.name,area=EXCLUDED.area,service=EXCLUDED.service,asset_type=EXCLUDED.asset_type,tag=EXCLUDED.tag,metadata=EXCLUDED.metadata,content=EXCLUDED.content",vals)
     total+=1
    documents+=1
   except Exception as exc: errors.append({'filename':filename,'error':str(exc)})
  status='READY' if documents and not errors else 'BLOCKED' if errors and not total else 'DATA_UPLOADED'; cur.execute(f"UPDATE anviqo_plant_onboarding SET status={p},updated_at={p} WHERE plant_id={p}",(status,_now(),plant_id))
 try: store.record_audit(a,'INGEST_PLANT_DATA','PLANT',plant_id,{'documents':documents,'records':total,'errors':len(errors)})
 except Exception: pass
 return {'status':'OK','plant_id':plant_id,'documents_processed':documents,'records_indexed':total,'errors':errors,'ingestion_version':INGESTION_VERSION,'safety':dict(SAFETY)}
def register(app):
 from flask import jsonify,request
 @app.post('/api/admin/onboarding/plant/<plant_id>/ingest')
 def ingest_route(plant_id):
  if not _plant_ok(plant_id): return jsonify({'status':'FORBIDDEN','message':'OWNER/ADMIN access to this plant is required'}),403
  try: return jsonify(ingest_plant(plant_id))
  except Exception as exc: return jsonify({'status':'ERROR','message':str(exc),'safety':dict(SAFETY)}),400
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
