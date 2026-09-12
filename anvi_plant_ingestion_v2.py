"""Durable universal plant-ingestion queue.

Web requests only create durable jobs. Actual ingestion is executed by a
separate worker process, so Render web-worker restarts cannot lose a job.
CHANGE DATA, NOT CODE. V5 intelligence and PLC/SCADA safety boundaries stay
untouched.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import anvi_tenant_store as store
from universal_onboarding import SAFETY

INGESTION_VERSION = "ANVIQO-PLANT-INGESTION-V2"
STALE_AFTER_MINUTES = 15


def _now(): return datetime.now(timezone.utc)
def _iso(dt): return dt.isoformat()
def _p(): return store._placeholder()


def _actor():
    from flask import session
    return {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}


def _plant_ok(plant_id, actor):
    if not actor.get("user_id") or not actor.get("organization_id") or actor.get("role") not in {"OWNER", "ADMIN"}: return False
    p = _p()
    with store._connect() as conn:
        cur = conn.cursor(); cur.execute(f"SELECT 1 FROM anviqo_plants WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE' LIMIT 1", (plant_id, actor["organization_id"]))
        return cur.fetchone() is not None


def init_schema():
    if not store.enabled(): return
    with store._connect() as conn:
        cur = conn.cursor()
        if store._is_sqlite():
            cur.execute("""CREATE TABLE IF NOT EXISTS anviqo_plant_ingestion_jobs (job_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, actor_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'QUEUED', message TEXT NOT NULL DEFAULT '', result_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT '', started_at TEXT, finished_at TEXT, updated_at TEXT NOT NULL DEFAULT '')""")
            for name, definition in [("actor_json","TEXT NOT NULL DEFAULT '{}'"),("status","TEXT NOT NULL DEFAULT 'QUEUED'"),("message","TEXT NOT NULL DEFAULT ''"),("result_json","TEXT NOT NULL DEFAULT '{}'"),("created_at","TEXT NOT NULL DEFAULT ''"),("started_at","TEXT"),("finished_at","TEXT"),("updated_at","TEXT NOT NULL DEFAULT ''")]:
                try: cur.execute(f"ALTER TABLE anviqo_plant_ingestion_jobs ADD COLUMN {name} {definition}")
                except Exception: pass
            cur.execute("CREATE INDEX IF NOT EXISTS idx_anviqo_ingest_jobs_status ON anviqo_plant_ingestion_jobs(status, created_at)")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS anviqo_plant_ingestion_jobs (job_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), plant_id TEXT NOT NULL REFERENCES anviqo_plants(plant_id), actor_json JSONB NOT NULL DEFAULT '{}'::jsonb, status TEXT NOT NULL DEFAULT 'QUEUED', message TEXT NOT NULL DEFAULT '', result_json JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
            for name, definition in [("actor_json","JSONB NOT NULL DEFAULT '{}'::jsonb"),("status","TEXT NOT NULL DEFAULT 'QUEUED'"),("message","TEXT NOT NULL DEFAULT ''"),("result_json","JSONB NOT NULL DEFAULT '{}'::jsonb"),("created_at","TIMESTAMPTZ NOT NULL DEFAULT NOW()"),("started_at","TIMESTAMPTZ"),("finished_at","TIMESTAMPTZ"),("updated_at","TIMESTAMPTZ NOT NULL DEFAULT NOW()")]:
                cur.execute(f"ALTER TABLE anviqo_plant_ingestion_jobs ADD COLUMN IF NOT EXISTS {name} {definition}")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_anviqo_ingest_jobs_status ON anviqo_plant_ingestion_jobs(status, created_at)")


def _parse_dt(value):
    if not value: return None
    if isinstance(value, datetime): return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    try: return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception: return None


def _stale_jobs():
    init_schema(); cutoff = _now() - timedelta(minutes=STALE_AFTER_MINUTES); p = _p()
    with store._connect() as conn:
        cur = conn.cursor(); cur.execute("SELECT job_id,started_at FROM anviqo_plant_ingestion_jobs WHERE status='RUNNING'")
        for job_id, started_at in cur.fetchall():
            dt = _parse_dt(started_at)
            if dt and dt < cutoff:
                cur.execute(f"UPDATE anviqo_plant_ingestion_jobs SET status={p},message={p},updated_at={p} WHERE job_id={p}", ("STALE", "Worker interruption detected; job is retryable.", _iso(_now()), job_id))


def _new_job_id(plant_id):
    import hashlib
    return "ing_" + hashlib.sha256(f"{plant_id}|{_iso(_now())}".encode()).hexdigest()[:24]


def enqueue_job(plant_id, actor):
    init_schema(); _stale_jobs(); p = _p(); now = _iso(_now())
    with store._connect() as conn:
        cur = conn.cursor(); cur.execute(f"SELECT job_id,status,created_at,updated_at FROM anviqo_plant_ingestion_jobs WHERE plant_id={p} AND organization_id={p} AND status IN ('QUEUED','RUNNING') ORDER BY created_at DESC LIMIT 1", (plant_id, actor["organization_id"]))
        existing = cur.fetchone()
        if existing: return {"job_id": existing[0], "job_status": existing[1], "created_at": str(existing[2]), "updated_at": str(existing[3]), "existing": True}
        job_id = _new_job_id(plant_id)
        cur.execute(f"INSERT INTO anviqo_plant_ingestion_jobs(job_id,organization_id,plant_id,actor_json,status,message,created_at,updated_at) VALUES({','.join([p]*8)})", (job_id, actor["organization_id"], plant_id, json.dumps(actor, separators=(",", ":")), "QUEUED", "Queued for universal ingestion worker.", now, now))
        try: cur.execute(f"UPDATE anviqo_plant_onboarding SET status='INDEXING',updated_at={p} WHERE plant_id={p}", (now, plant_id))
        except Exception: pass
    return {"job_id": job_id, "job_status": "QUEUED", "created_at": now, "updated_at": now, "existing": False}


def ingest_plant(plant_id, actor=None):
    if not actor or not _plant_ok(plant_id, actor): raise PermissionError("OWNER/ADMIN access to this plant is required")
    import anvi_plant_ingestion_runtime as runtime
    result = runtime.ingest_plant(plant_id, actor); result["ingestion_version"] = INGESTION_VERSION; result["safety"] = dict(SAFETY); return result


def run_pending_jobs(limit=1):
    init_schema(); _stale_jobs(); p = _p(); processed = 0
    while processed < max(1, int(limit)):
        with store._connect() as conn:
            cur = conn.cursor(); cur.execute("SELECT job_id,plant_id,organization_id,actor_json FROM anviqo_plant_ingestion_jobs WHERE status='QUEUED' ORDER BY created_at LIMIT 1"); row = cur.fetchone()
            if not row: break
            job_id, plant_id, organization_id, actor_raw = row; actor = actor_raw if isinstance(actor_raw, dict) else json.loads(actor_raw or "{}")
            cur.execute(f"UPDATE anviqo_plant_ingestion_jobs SET status={p},message={p},started_at={p},updated_at={p} WHERE job_id={p} AND status='QUEUED'", ("RUNNING", "Worker claimed ingestion job.", _iso(_now()), job_id))
        try:
            result = ingest_plant(plant_id, actor); status = "COMPLETED" if result.get("status") == "OK" and not result.get("errors") else "COMPLETED_WITH_ERRORS"; message = f"Processed {result.get('documents_processed', 0)} documents and indexed {result.get('records_indexed', 0)} records."
        except Exception as exc:
            result = {"status":"ERROR","plant_id":plant_id,"message":str(exc),"safety":dict(SAFETY)}; status="FAILED"; message=str(exc)
        with store._connect() as conn:
            cur = conn.cursor(); cur.execute(f"UPDATE anviqo_plant_ingestion_jobs SET status={p},message={p},result_json={p},finished_at={p},updated_at={p} WHERE job_id={p}", (status,message,json.dumps(result,default=str),_iso(_now()),job_id))
        processed += 1
    return {"processed": processed, "safety": dict(SAFETY)}


def register(app):
    from flask import jsonify
    init_schema()
    @app.post('/api/admin/onboarding/plant/<plant_id>/ingest')
    def ingestion_start_v2(plant_id):
        actor=_actor()
        if not _plant_ok(plant_id,actor): return jsonify({'status':'FORBIDDEN','message':'OWNER/ADMIN access to this plant is required'}),403
        job=enqueue_job(plant_id,actor)
        return jsonify({'status':'QUEUED','job_status':job['job_status'],'job_id':job['job_id'],'plant_id':plant_id,'message':'Universal ingestion is queued for the durable worker. Web-worker restarts will not lose the job.','safety':dict(SAFETY)}),202
    @app.get('/api/admin/onboarding/plant/<plant_id>/ingest-status')
    def ingestion_status_v2(plant_id):
        actor=_actor()
        if not _plant_ok(plant_id,actor): return jsonify({'status':'FORBIDDEN'}),403
        _stale_jobs(); p=_p()
        with store._connect() as conn:
            cur=conn.cursor(); cur.execute(f"SELECT job_id,status,message,result_json,created_at,started_at,finished_at,updated_at FROM anviqo_plant_ingestion_jobs WHERE plant_id={p} AND organization_id={p} ORDER BY created_at DESC LIMIT 1",(plant_id,actor['organization_id'])); row=cur.fetchone()
        if not row: return jsonify({'status':'IDLE','job_status':'IDLE','plant_id':plant_id,'safety':dict(SAFETY)})
        result=row[3] if isinstance(row[3],dict) else json.loads(row[3] or '{}')
        return jsonify({'status':'OK','job_id':row[0],'job_status':row[1],'message':row[2],'result':result,'created_at':str(row[4]),'started_at':str(row[5]) if row[5] else None,'finished_at':str(row[6]) if row[6] else None,'updated_at':str(row[7]),'plant_id':plant_id,'safety':dict(SAFETY)})
    return app

__all__=['register','init_schema','enqueue_job','ingest_plant','run_pending_jobs']
