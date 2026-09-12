"""Durable universal plant-ingestion queue.

Web requests enqueue durable jobs. A separate worker can claim queued jobs through
a protected dispatch endpoint, while durable state still supports restart recovery.
CHANGE DATA, NOT CODE.
"""
from __future__ import annotations
import json, os, threading, time
from datetime import datetime, timezone, timedelta
import anvi_tenant_store as store
from universal_onboarding import SAFETY
INGESTION_VERSION="ANVIQO-PLANT-INGESTION-V2"
STALE_AFTER_MINUTES=60
_WORKER_STARTED=False
_WORKER_LOCK=threading.Lock()

def _now(): return datetime.now(timezone.utc)
def _iso(dt): return dt.isoformat()
def _p(): return store._placeholder()

def _actor():
 from flask import session
 return {"user_id":session.get("user_id",""),"organization_id":session.get("organization_id",""),"plant_id":session.get("plant_id",""),"role":session.get("role",""),"username":session.get("username","")}

def _plant_ok(plant_id,actor):
 if not actor.get("user_id") or not actor.get("organization_id") or actor.get("role") not in {"OWNER","ADMIN"}: return False
 p=_p()
 with store._connect() as conn:
  cur=conn.cursor(); cur.execute(f"SELECT 1 FROM anviqo_plants WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE' LIMIT 1",(plant_id,actor["organization_id"]))
  return cur.fetchone() is not None

def init_schema():
 if not store.enabled(): return
 with store._connect() as conn:
  cur=conn.cursor()
  if store._is_sqlite():
   cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_ingestion_jobs (job_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, actor_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'QUEUED', message TEXT NOT NULL DEFAULT '', result_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT '', started_at TEXT, finished_at TEXT, updated_at TEXT NOT NULL DEFAULT '')")
  else:
   cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_ingestion_jobs (job_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), plant_id TEXT NOT NULL REFERENCES anviqo_plants(plant_id), actor_json JSONB NOT NULL DEFAULT '{}'::jsonb, status TEXT NOT NULL DEFAULT 'QUEUED', message TEXT NOT NULL DEFAULT '', result_json JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
   for n,d in [("job_id","TEXT"),("organization_id","TEXT"),("plant_id","TEXT"),("actor_json","JSONB NOT NULL DEFAULT '{}'::jsonb"),("status","TEXT NOT NULL DEFAULT 'QUEUED'"),("message","TEXT NOT NULL DEFAULT ''"),("result_json","JSONB NOT NULL DEFAULT '{}'::jsonb"),("created_at","TIMESTAMPTZ NOT NULL DEFAULT NOW()"),("started_at","TIMESTAMPTZ"),("finished_at","TIMESTAMPTZ"),("updated_at","TIMESTAMPTZ NOT NULL DEFAULT NOW()")] :
    cur.execute(f"ALTER TABLE anviqo_plant_ingestion_jobs ADD COLUMN IF NOT EXISTS {n} {d}")
   cur.execute("CREATE INDEX IF NOT EXISTS idx_anviqo_ingest_jobs_status ON anviqo_plant_ingestion_jobs(status, created_at)")

def _parse_dt(v):
 if not v:return None
 if isinstance(v,datetime):return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
 try:return datetime.fromisoformat(str(v).replace("Z","+00:00"))
 except Exception:return None

def _stale_jobs():
 init_schema();cutoff=_now()-timedelta(minutes=STALE_AFTER_MINUTES);p=_p()
 with store._connect() as conn:
  cur=conn.cursor();cur.execute("SELECT job_id,plant_id,organization_id,started_at FROM anviqo_plant_ingestion_jobs WHERE status='RUNNING'")
  for jid,plant_id,organization_id,started in cur.fetchall():
   dt=_parse_dt(started)
   if dt is None or dt<cutoff:
    cur.execute(f"UPDATE anviqo_plant_ingestion_jobs SET status={p},message={p},updated_at={p} WHERE job_id={p}",( "STALE","Worker interruption detected; job is retryable.",_iso(_now()),jid))
    try: cur.execute(f"UPDATE anviqo_plant_onboarding SET status='DATA_UPLOADED',updated_at={p} WHERE plant_id={p} AND organization_id={p}",(_iso(_now()),plant_id,organization_id))
    except Exception: pass

def _new_job_id(plant_id):
 import hashlib
 return "ing_"+hashlib.sha256(f"{plant_id}|{_iso(_now())}".encode()).hexdigest()[:24]

def enqueue_job(plant_id,actor):
 init_schema();_stale_jobs();p=_p();now=_iso(_now())
 with store._connect() as conn:
  cur=conn.cursor();cur.execute(f"SELECT job_id,status,created_at,updated_at FROM anviqo_plant_ingestion_jobs WHERE plant_id={p} AND organization_id={p} AND status IN ('QUEUED','RUNNING') ORDER BY created_at DESC LIMIT 1",(plant_id,actor["organization_id"]))
  old=cur.fetchone()
  if old:return {"job_id":old[0],"job_status":old[1],"created_at":str(old[2]),"updated_at":str(old[3]),"existing":True}
  jid=_new_job_id(plant_id);cur.execute(f"INSERT INTO anviqo_plant_ingestion_jobs(job_id,organization_id,plant_id,actor_json,status,message,created_at,updated_at) VALUES({','.join([p]*8)})",(jid,actor["organization_id"],plant_id,json.dumps(actor,separators=(",",":")),"QUEUED","Queued for universal ingestion worker.",now,now))
  try:cur.execute(f"UPDATE anviqo_plant_onboarding SET status='INDEXING',updated_at={p} WHERE plant_id={p} AND organization_id={p}",(now,plant_id,actor["organization_id"]))
  except Exception:pass
 return {"job_id":jid,"job_status":"QUEUED","created_at":now,"updated_at":now,"existing":False}

def ingest_plant(plant_id,actor=None):
 if not actor or not _plant_ok(plant_id,actor):raise PermissionError("OWNER/ADMIN access to this plant is required")
 import anvi_plant_ingestion_runtime as runtime
 r=runtime.ingest_plant(plant_id,actor);r["ingestion_version"]=INGESTION_VERSION;r["safety"]=dict(SAFETY);return r

def run_pending_jobs(limit=1):
 init_schema();_stale_jobs();p=_p();processed=0
 while processed<max(1,int(limit)):
  with store._connect() as conn:
   cur=conn.cursor();cur.execute("SELECT job_id,plant_id,organization_id,actor_json FROM anviqo_plant_ingestion_jobs WHERE status='QUEUED' ORDER BY created_at LIMIT 1");row=cur.fetchone()
   if not row:break
   jid,plant,org,raw=row;actor=raw if isinstance(raw,dict) else json.loads(raw or "{}")
   cur.execute(f"UPDATE anviqo_plant_ingestion_jobs SET status={p},message={p},started_at={p},updated_at={p} WHERE job_id={p} AND status='QUEUED'",("RUNNING","Worker claimed ingestion job.",_iso(_now()),jid))
  try:
   r=ingest_plant(plant,actor);status="COMPLETED" if r.get("status")=="OK" and not r.get("errors") else "COMPLETED_WITH_ERRORS";msg=f"Processed {r.get('documents_processed',0)} documents and indexed {r.get('records_indexed',0)} records."
  except Exception as exc:r={"status":"ERROR","plant_id":plant,"message":str(exc),"safety":dict(SAFETY)};status="FAILED";msg=str(exc)
  with store._connect() as conn:
   cur=conn.cursor();cur.execute(f"UPDATE anviqo_plant_ingestion_jobs SET status={p},message={p},result_json={p},finished_at={p},updated_at={p} WHERE job_id={p}",(status,msg,json.dumps(r,default=str),_iso(_now()),jid))
   try:
    if status in {"COMPLETED","COMPLETED_WITH_ERRORS"}: cur.execute(f"UPDATE anviqo_plant_onboarding SET status={p},updated_at={p} WHERE plant_id={p} AND organization_id={p}",(status,_iso(_now()),plant,org))
    elif status=="FAILED": cur.execute(f"UPDATE anviqo_plant_onboarding SET status='ERROR',updated_at={p} WHERE plant_id={p} AND organization_id={p}",(_iso(_now()),plant,org))
   except Exception: pass
  processed+=1
 return {"processed":processed,"safety":dict(SAFETY)}

def _dispatch_once():
 try:
  result=run_pending_jobs(1)
  print(f"ANVI ingestion dispatcher: processed={result.get('processed',0)}",flush=True)
 except Exception as exc:
  print(f"ANVI ingestion dispatcher error: {exc}",flush=True)

def _recovery_loop():
 while True:
  try: run_pending_jobs(1)
  except Exception as exc: print(f"ANVI ingestion recovery worker: {exc}",flush=True)
  time.sleep(5)

def _start_recovery_worker():
 global _WORKER_STARTED
 with _WORKER_LOCK:
  if _WORKER_STARTED:return
  _WORKER_STARTED=True
  threading.Thread(target=_recovery_loop,daemon=True,name="anvi-ingestion-recovery").start()

def _latest_job(plant_id,organization_id):
 p=_p()
 with store._connect() as conn:
  cur=conn.cursor();cur.execute(f"SELECT job_id,status,message,result_json,created_at,started_at,finished_at,updated_at FROM anviqo_plant_ingestion_jobs WHERE plant_id={p} AND organization_id={p} ORDER BY created_at DESC LIMIT 1",(plant_id,organization_id));return cur.fetchone()

def register(app):
 from flask import jsonify, request
 init_schema();_start_recovery_worker()
 @app.post('/api/internal/ingestion/dispatch')
 def ingestion_internal_dispatch():
  expected=os.environ.get('ANVI_INGESTION_DISPATCH_TOKEN','').strip()
  supplied=request.headers.get('X-ANVI-INGESTION-TOKEN','').strip()
  if not expected or supplied != expected:return jsonify({'status':'FORBIDDEN'}),403
  return jsonify(run_pending_jobs(1))
 @app.post('/api/admin/onboarding/plant/<plant_id>/ingest')
 def ingestion_start_v2(plant_id):
  actor=_actor()
  if not _plant_ok(plant_id,actor):return jsonify({'status':'FORBIDDEN','message':'OWNER/ADMIN access to this plant is required'}),403
  job=enqueue_job(plant_id,actor)
  _dispatch_once()
  row=_latest_job(plant_id,actor['organization_id'])
  return jsonify({'status':'OK' if row and row[1] in {'COMPLETED','COMPLETED_WITH_ERRORS'} else 'QUEUED','job_status':row[1] if row else job['job_status'],'job_id':row[0] if row else job['job_id'],'plant_id':plant_id,'message':row[2] if row else 'Universal ingestion queued.','result':(row[3] if isinstance(row[3],dict) else json.loads(row[3] or '{}')) if row else {},'safety':dict(SAFETY)}),200 if row and row[1] in {'COMPLETED','COMPLETED_WITH_ERRORS'} else 202
 @app.get('/api/admin/onboarding/plant/<plant_id>/ingest-status')
 def ingestion_status_v2(plant_id):
  actor=_actor()
  if not _plant_ok(plant_id,actor):return jsonify({'status':'FORBIDDEN'}),403
  _stale_jobs()
  row=_latest_job(plant_id,actor['organization_id'])
  if row and row[1]=='QUEUED':
   _dispatch_once()
   row=_latest_job(plant_id,actor['organization_id'])
  if not row:return jsonify({'status':'IDLE','job_status':'IDLE','plant_id':plant_id,'safety':dict(SAFETY)})
  result=row[3] if isinstance(row[3],dict) else json.loads(row[3] or '{}')
  return jsonify({'status':'OK','job_id':row[0],'job_status':row[1],'message':row[2],'result':result,'created_at':str(row[4]),'started_at':str(row[5]) if row[5] else None,'finished_at':str(row[6]) if row[6] else None,'updated_at':str(row[7]),'plant_id':plant_id,'safety':dict(SAFETY)})
 return app

__all__=['register','init_schema','enqueue_job','ingest_plant','run_pending_jobs']