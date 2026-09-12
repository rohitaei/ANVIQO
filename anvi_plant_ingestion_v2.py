"""Clean universal ingestion runner.

Legacy ingestion jobs are deliberately ignored. This runner uses a separate
v3 table and fresh job ids. CHANGE DATA, NOT CODE. V5 remains frozen/read-only.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone

import anvi_tenant_store as store
from universal_onboarding import SAFETY

TABLE = "anviqo_plant_ingestion_runs"
INGESTION_VERSION = "ANVIQO-UNIVERSAL-INGESTION-V3"


def _p():
    return store._placeholder()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _actor():
    from flask import session
    return {k: session.get(k, "") for k in ("user_id", "organization_id", "plant_id", "role", "username")}


def _plant_ok(pid, actor):
    if not actor.get("user_id") or not actor.get("organization_id") or actor.get("role") not in {"OWNER", "ADMIN"}:
        return False
    p = _p()
    with store._connect() as conn:
        q = conn.cursor()
        q.execute(f"SELECT 1 FROM anviqo_plants WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE' LIMIT 1", (pid, actor["organization_id"]))
        return q.fetchone() is not None


def init_schema():
    if not store.enabled():
        return
    with store._connect() as conn:
        q = conn.cursor()
        if store._is_sqlite():
            q.execute(f"CREATE TABLE IF NOT EXISTS {TABLE} (job_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, actor_json TEXT NOT NULL DEFAULT '{{}}', status TEXT NOT NULL DEFAULT 'QUEUED', message TEXT NOT NULL DEFAULT '', result_json TEXT NOT NULL DEFAULT '{{}}', created_at TEXT NOT NULL DEFAULT '', started_at TEXT, finished_at TEXT, updated_at TEXT NOT NULL DEFAULT '')")
        else:
            q.execute(f"CREATE TABLE IF NOT EXISTS {TABLE} (job_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), plant_id TEXT NOT NULL REFERENCES anviqo_plants(plant_id), actor_json JSONB NOT NULL DEFAULT '{{}}'::jsonb, status TEXT NOT NULL DEFAULT 'QUEUED', message TEXT NOT NULL DEFAULT '', result_json JSONB NOT NULL DEFAULT '{{}}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")


def enqueue_job(pid, actor):
    init_schema()
    p = _p()
    now = _now()
    with store._connect() as conn:
        q = conn.cursor()
        q.execute(f"SELECT job_id,status FROM {TABLE} WHERE plant_id={p} AND organization_id={p} AND status IN ('QUEUED','RUNNING') ORDER BY created_at DESC LIMIT 1", (pid, actor["organization_id"]))
        old = q.fetchone()
        if old:
            return {"job_id": old[0], "job_status": old[1], "existing": True}
        jid = "ingv3_" + uuid.uuid4().hex
        q.execute(f"INSERT INTO {TABLE}(job_id,organization_id,plant_id,actor_json,status,message,created_at,updated_at) VALUES({','.join([p] * 8)})", (jid, actor["organization_id"], pid, json.dumps(actor, separators=(",", ":")), "QUEUED", "Queued for clean universal ingestion.", now, now))
    return {"job_id": jid, "job_status": "QUEUED", "existing": False, "created_at": now, "updated_at": now}


def ingest_plant(pid, actor=None):
    if not actor or not _plant_ok(pid, actor):
        raise PermissionError("OWNER/ADMIN access to this plant is required")
    import anvi_plant_ingestion_runtime as runtime
    result = runtime.ingest_plant(pid, actor)
    result["ingestion_version"] = INGESTION_VERSION
    result["safety"] = dict(SAFETY)
    return result


def _finish(jid, pid, org, actor):
    try:
        r = ingest_plant(pid, actor)
        status = "COMPLETED" if r.get("status") == "OK" and not r.get("errors") else "COMPLETED_WITH_ERRORS"
        msg = f"Processed {r.get('documents_processed', 0)} documents and indexed {r.get('records_indexed', 0)} records."
    except Exception as e:
        r = {"status": "ERROR", "plant_id": pid, "message": str(e), "safety": dict(SAFETY)}
        status = "FAILED"
        msg = str(e)
    now = _now()
    p = _p()
    with store._connect() as conn:
        q = conn.cursor()
        q.execute(f"UPDATE {TABLE} SET status={p},message={p},result_json={p},finished_at={p},updated_at={p} WHERE job_id={p}", (status, msg, json.dumps(r, default=str), now, now, jid))


def _claim_job():
    init_schema()
    p = _p()
    with store._connect() as conn:
        q = conn.cursor()
        q.execute(f"SELECT job_id,plant_id,organization_id,actor_json FROM {TABLE} WHERE status='QUEUED' ORDER BY created_at LIMIT 1")
        row = q.fetchone()
        if not row:
            return None
        jid, pid, org, raw = row
        actor = raw if isinstance(raw, dict) else json.loads(raw or "{}")
        now = _now()
        q.execute(f"UPDATE {TABLE} SET status={p},message={p},started_at={p},updated_at={p} WHERE job_id={p} AND status='QUEUED'", ("RUNNING", "Worker claimed clean ingestion job.", now, now, jid))
        if getattr(q, "rowcount", 1) != 1:
            return None
    return jid, pid, org, actor


def _dispatch_once():
    x = _claim_job()
    if not x:
        return {"processed": 0, "queued_only": True, "safety": dict(SAFETY)}
    jid, pid, org, actor = x
    threading.Thread(target=_finish, args=x, daemon=True, name=f"anvi-clean-ingest-{jid}").start()
    return {"processed": 1, "job_id": jid, "status": "RUNNING", "safety": dict(SAFETY)}


def register(app):
    init_schema()

    @app.post("/api/admin/onboarding/plant/<plant_id>/ingest")
    def start(plant_id):
        from flask import jsonify
        actor = _actor()
        if not _plant_ok(plant_id, actor):
            return jsonify({"error": "OWNER/ADMIN access to this plant is required"}), 403
        return jsonify(enqueue_job(plant_id, actor)), 202

    @app.get("/api/admin/onboarding/plant/<plant_id>/ingest/status")
    def status(plant_id):
        from flask import jsonify
        actor = _actor()
        if not _plant_ok(plant_id, actor):
            return jsonify({"error": "OWNER/ADMIN access to this plant is required"}), 403
        p = _p()
        with store._connect() as conn:
            q = conn.cursor()
            q.execute(f"SELECT job_id,status,message,result_json,created_at,started_at,finished_at,updated_at FROM {TABLE} WHERE plant_id={p} AND organization_id={p} ORDER BY created_at DESC LIMIT 1", (plant_id, actor["organization_id"]))
            row = q.fetchone()
        if not row:
            return jsonify({"status": "NOT_STARTED", "job_status": "NOT_STARTED"})
        jid, st, msg, r, cr, ss, ff, up = row
        if isinstance(r, str):
            try:
                r = json.loads(r or "{}")
            except Exception:
                r = {}
        return jsonify({"job_id": jid, "status": st, "job_status": st, "message": msg, "result": r or {}, "created_at": str(cr), "started_at": str(ss) if ss else None, "finished_at": str(ff) if ff else None, "updated_at": str(up) if up else None})

    @app.post("/api/internal/ingestion/dispatch")
    def dispatch():
        from flask import jsonify
        return jsonify(_dispatch_once())
