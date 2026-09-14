"""ANVIQO durable plant-data import worker.

The queue is persisted in PostgreSQL, so a worker restart does not lose an
import request. The web service only enqueues work and never performs the
long-running import inside the HTTP request.
"""
from __future__ import annotations
import json, os, threading, time
from flask import Flask, jsonify
import anvi_tenant_store as store
import anvi_plant_data_import as direct

app = Flask(__name__)
_STOP = threading.Event()

def _p(): return store._placeholder()
def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

def _claim():
    direct._job_schema(); p=_p(); now=_now()
    with store._connect() as conn:
        cur=conn.cursor()
        cur.execute(f"SELECT job_id,plant_id,organization_id,actor_json FROM {direct.JOB_TABLE} WHERE status='QUEUED' ORDER BY created_at LIMIT 1")
        row=cur.fetchone()
        if not row:return None
        jid,plant_id,org,raw=row
        actor=raw if isinstance(raw,dict) else json.loads(raw or "{}")
        cur.execute(f"UPDATE {direct.JOB_TABLE} SET status={p},message={p},started_at={p},updated_at={p} WHERE job_id={p} AND status='QUEUED'",("RUNNING","Plant-data import worker started.",now,now,jid))
        if getattr(cur,"rowcount",1)!=1:return None
    return jid,plant_id,org,actor

def _finish(jid,plant_id,org,status,message,result):
    p=_p(); now=_now()
    with store._connect() as conn:
        conn.cursor().execute(f"UPDATE {direct.JOB_TABLE} SET status={p},message={p},result_json={p},finished_at={p},updated_at={p} WHERE job_id={p}",(status,message,json.dumps(result,default=str),now,now,jid))
    try:
        with store._connect() as conn:
            target="READY" if status=="COMPLETED" else "DATA_UPLOADED"
            conn.cursor().execute(f"UPDATE anviqo_plant_onboarding SET status={p},updated_at={p} WHERE plant_id={p} AND organization_id={p}",(target,now,plant_id,org))
    except Exception:
        pass

def _process_once():
    job=_claim()
    if not job:return False
    jid,plant_id,org,actor=job
    try:
        result=direct.import_plant_data(plant_id,actor)
        status="COMPLETED" if result.get("status")=="OK" and not result.get("errors") else "COMPLETED_WITH_ERRORS"
        message=f"Processed {result.get('documents_processed',0)} document(s) and made {result.get('records_available_to_anvi',0)} knowledge record(s) available to ANVI."
    except Exception as exc:
        result={"status":"ERROR","plant_id":plant_id,"message":str(exc),"errors":[{"error":str(exc)}],"safety":dict(direct.SAFETY)}
        status="FAILED"; message=str(exc)
    _finish(jid,plant_id,org,status,message,result)
    print(f"ANVIQO IMPORT {jid} {status}: {message}",flush=True)
    return True

def _worker_loop():
    direct._job_schema()
    while not _STOP.is_set():
        try:
            if not _process_once():_STOP.wait(2)
        except Exception as exc:
            print(f"ANVIQO IMPORT WORKER ERROR: {exc}",flush=True)
            _STOP.wait(5)

@app.get("/health")
def health():
    return jsonify({"status":"READY","service":"anviqo-plant-import-worker","queue":"postgres-durable","safety":dict(direct.SAFETY)})

if __name__ == "__main__":
    threading.Thread(target=_worker_loop,daemon=True,name="anviqo-import-worker").start()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","10000")),threaded=True)
