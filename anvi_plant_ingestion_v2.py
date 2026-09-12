"""Durable universal plant-ingestion queue.

Web requests enqueue durable jobs. A separate worker claims queued jobs through
a bounded dispatch endpoint, while durable state still supports restart recovery.
CHANGE DATA, NOT CODE.
"""
from __future__ import annotations
import json, os, threading, time
from datetime import datetime, timezone, timedelta
import anvi_tenant_store as store
from universal_onboarding import SAFETY
INGESTION_VERSION="ANVIQO-PLANT-INGESTION-V2"
STALE_AFTER_MINUTES=5
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
   cur.execute("ALTER TABLE anviqo_plant_ingestion_jobs ADD COLUMN IF NOT EXISTS job_id TEXT")
   cur.execute("UPDATE anviqo_plant_ingestion_jobs SET job_id='ing_legacy_' || md5(coalesce(plant_id,'') || '|' || coalesce(created_at::text,'')) WHERE job_id IS NULL")
   for n,d in [("organization_id","TEXT"),("plant_id","TEXT"),("actor_json","JSONB NOT NULL DEFAULT '{}'::jsonb"),("status","TEXT NOT NULL DEFAULT 'QUEUED'"),("message","TEXT NOT NULL DEFAULT ''"),("result_json","JSONB NOT NULL DEFAULT '{}'::jsonb"),("created_at","TIMESTAMPTZ NOT NULL DEFAULT NOW()"),("started_at","TIMESTAMPTZ"),("finished_at","TIMESTAMPTZ"),("updated_at","TIMESTAMPTZ NOT NULL DEFAULT NOW()")] :
    cur.execute(f"ALTER TABLE anviqo_plant_ingestion_jobs ADD COLUMN IF NOT EXISTS {n} {d}")
   cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_anviqo_ingest_jobs_job_id ON anviqo_plant_ingestion_jobs(job_id) WHERE job_id IS NOT NULL")
   # Older deployments used plant_id as the table primary key. The queue now
   # supports multiple durable jobs per plant, so the primary key must be job_id.
   cur.execute("ALTER TABLE anviqo_plant_ingestion_jobs DROP CONSTRAINT IF EXISTS anviqo_plant_ingestion_jobs_pkey")
   cur.execute("ALTER TABLE anviqo_plant_ingestion_jobs ADD CONSTRAINT anviqo_plant_ingestion_jobs_pkey PRIMARY KEY (job_id)")
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
    cur.execute(f"UPDATE anviqo_plant_ingestion_jobs SET status={p},message={p},started_at=NULL,finished_at=NULL,updated_at={p} WHERE job_id={p} AND status='RUNNING'",("QUEUED","Recovered orphaned ingestion job; retrying with the dedicated worker.",_iso(_now()),jid))
    try: cur.execute(f"UPDATE anviqo_plant_onboarding SET status='INDEXING',updated_at={p} WHERE plant_id={p} AND organization_id={p}",(_iso(_now()),plant_id,organization_id))
    except Exception: pass

def _new_job_id(plant_id):
 import uuid
 return "ing_"+uuid.uuid4().hex

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

def _finish_job(jid,plant,org,actor):
 try:
  r=ingest_plant(plant,actor);status="COMPLETED" if r.get("status")=="OK" and not r.get("errors") else "COMPLETED_WITH_ERRORS";msg=f"Processed {r.get('documents_processed',0)} documents and indexed {r.get('records_indexed',0)} records."
 except Exception as exc:r={"status":"ERROR","plant_id":plant,"message":str(exc),"safety":dict(SAFETY)};status="FAILED";msg=str(exc)
 try:
  with store._connect() as conn:
   cur=conn.cursor();cur.execute(f"UPDATE anviqo_plant_ingestion_jobs SET status={_p()},message={_p()},result_json={_p()},finished_at={_p()},updated_at={_p()} WHERE job_id={_p()}",(status,msg,json.dumps(r,default=str),_iso(_now()),_iso(_now()),jid))
   if status in {"COMPLETED","COMPLETED_WITH_ERRORS"}: cur.execute(f"UPDATE anviqo_plant_onboarding SET status={_p()},updated_at={_p()} WHERE plant_id={_p()} AND organization_id={_p()}",( "DATA_UPLOADED",_iso(_now()),plant,org))
   elif status=="FAILED": cur.execute(f"UPDATE anviqo_plant_onboarding SET status='ERROR',updated_at={_p()} WHERE plant_id={_p()} AND organization_id={_p()}",(_iso(_now()),plant,org))
 except Exception as exc: print(f"ANVI ingestion job {jid} finalization error: {exc}",flush=True)

def _claim_job():
 init_schema();_stale_jobs();p=_p()
 with store._connect() as conn:
  cur=conn.cursor();cur.execute("SELECT job_id,plant_id,organization_id,actor_json FROM anviqo_plant_ingestion_jobs WHERE status='QUEUED' ORDER BY created_at LIMIT 1");row=cur.fetchone()
  if not row:return None
  jid,plant,org,raw=row;actor=raw if isinstance(raw,dict) else json.loads(raw or "{}")
  now=_iso(_now())
  cur.execute(f"UPDATE anviqo_plant_ingestion_jobs SET status={p},message={p},started_at={p},updated_at={p} WHERE job_id={p} AND status='QUEUED'",("RUNNING","Worker claimed ingestion job.",now,now,jid))
  if cur.rowcount != 1:return None
 return jid,plant,org,actor

def run_pending_jobs(limit=1):
 processed=0
 while processed<max(1,int(limit)):
  claimed=_claim_job()
  if not claimed:break
  jid,plant,org,actor=claimed
  _finish_job(jid,plant,org,actor)
  processed+=1
 return {"processed":processed,"safety":dict(SAFETY)}

def _dispatch_once():
 claimed=_claim_job()
 if not claimed:return {"processed":0,"queued_only":True,"safety":dict(SAFETY)}
 jid,plant,org,actor=claimed
 threading.Thread(target=_finish_job,args=(jid,plant,org,actor),daemon=True,name=f"anvi-ingest-{jid}").start()
 return {"processed":1,"job_id":jid,"status":"RUNNING","safety":dict(SAFETY)}

def _recovery_loop():
 while True:
  try: run_pending_jobs(1)
  except Exception as exc: print(f"ANVI ingestion recovery worker error: {exc}",flush=True)
  time.sleep(5)

def _start_recovery_worker():
 global _WORKER_STARTED
 with _WORKER_LOCK:
  if _WORKER_STARTED:return
  _WORKER_STARTED=True
  threading.Thread(target=_recovery_loop,daemon=True,name="anvi-ingestion-recovery").start()

def register(app):
 init_schema()
 @app.post("/api/admin/onboarding/plant/<plant_id>/ingest")
 def ingestion_start(plant_id):
  from flask import jsonify
  actor=_actor()
  if not _plant_ok(plant_id,actor):return jsonify({"error":"OWNER/ADMIN access to this plant is required"}),403
  return jsonify(enqueue_job(plant_id,actor)),202
 @app.get("/api/admin/onboarding/plant/<plant_id>/ingest/status")
 def ingestion_status(plant_id):
  from flask import jsonify
  actor=_actor();p=_p()
  if not _plant_ok(plant_id,actor):return jsonify({"error":"OWNER/ADMIN access to this plant is required"}),403
  with store._connect() as conn:
   cur=conn.cursor();cur.execute(f"SELECT job_id,status,message,result_json,created_at,started_at,finished_at,updated_at FROM anviqo_plant_ingestion_jobs WHERE plant_id={p} AND organization_id={p} ORDER BY created_at DESC LIMIT 1",(plant_id,actor["organization_id"]));row=cur.fetchone()
  if not row:return jsonify({"status":"NOT_STARTED","job_status":"NOT_STARTED"})
  jid,status,msg,result,created,started,finished,updated=row
  if isinstance(result,str):
   try:result=json.loads(result or "{}")
   except Exception:result={}
  return jsonify({"job_id":jid,"status":status,"job_status":status,"message":msg,"result":result or {},"created_at":str(created),"started_at":str(started) if started else None,"finished_at":str(finished) if finished else None,"updated_at":str(updated) if updated else None})
 @app.post("/api/internal/ingestion/dispatch")
 def ingestion_internal_dispatch():
  from flask import jsonify
  return jsonify(_dispatch_once())