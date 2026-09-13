"""Universal plant ingestion runner. Legacy ingestion jobs are ignored. CHANGE DATA, NOT CODE."""
from __future__ import annotations
import json, uuid, os
from datetime import datetime, timezone
import anvi_tenant_store as store
from universal_onboarding import SAFETY

TABLE = "anviqo_universal_ingestion_jobs"
VERSION = "ANVIQO-UNIVERSAL-INGESTION-V6-DIRECT"

def p(): return store._placeholder()
def now(): return datetime.now(timezone.utc).isoformat()

def actor():
    from flask import session
    return {k: session.get(k, "") for k in ("user_id", "organization_id", "plant_id", "role", "username")}

def ok(pid, a):
    if not a.get("user_id") or not a.get("organization_id") or a.get("role") not in {"OWNER", "ADMIN"}:
        return False
    with store._connect() as c:
        q = c.cursor()
        q.execute(
            f"SELECT 1 FROM anviqo_plants WHERE plant_id={p()} AND organization_id={p()} AND status='ACTIVE' LIMIT 1",
            (pid, a["organization_id"]),
        )
        return q.fetchone() is not None

def init_schema():
    if not store.enabled(): return
    with store._connect() as c:
        q = c.cursor(); ph = p()
        if store._is_sqlite():
            q.execute(f"CREATE TABLE IF NOT EXISTS {TABLE}(job_id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,plant_id TEXT NOT NULL,actor_json TEXT NOT NULL,status TEXT NOT NULL,message TEXT NOT NULL,result_json TEXT NOT NULL DEFAULT '{{}}',created_at TEXT NOT NULL,started_at TEXT,finished_at TEXT,updated_at TEXT NOT NULL)")
        else:
            q.execute(f"CREATE TABLE IF NOT EXISTS {TABLE}(job_id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id),plant_id TEXT NOT NULL REFERENCES anviqo_plants(plant_id),actor_json JSONB NOT NULL,status TEXT NOT NULL,message TEXT NOT NULL,result_json JSONB NOT NULL DEFAULT '{{}}'::jsonb,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),started_at TIMESTAMPTZ,finished_at TIMESTAMPTZ,updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")

def reconcile_legacy_ui(pid, a):
    ph = p()
    try:
        with store._connect() as c:
            q = c.cursor()
            q.execute(f"SELECT status FROM {TABLE} WHERE plant_id={ph} AND organization_id={ph} ORDER BY created_at DESC LIMIT 1", (pid, a["organization_id"]))
            r = q.fetchone(); latest = str(r[0]).upper() if r else "NOT_STARTED"
            if latest in {"QUEUED", "RUNNING"}: return latest
            target = "READY" if latest == "COMPLETED" else "DATA_UPLOADED"
            q.execute(f"UPDATE anviqo_plant_onboarding SET status={ph},updated_at={ph} WHERE plant_id={ph} AND organization_id={ph} AND status='INDEXING'", (target, now(), pid, a["organization_id"]))
            return latest
    except Exception:
        return "UNKNOWN"

def enqueue(pid, a):
    init_schema(); ph = p(); t = now(); jid = "ingv6_" + uuid.uuid4().hex
    with store._connect() as c:
        q = c.cursor()
        q.execute(f"SELECT job_id,status FROM {TABLE} WHERE plant_id={ph} AND organization_id={ph} AND status IN('QUEUED','RUNNING') ORDER BY created_at DESC LIMIT 1", (pid, a["organization_id"]))
        r = q.fetchone()
        if r:
            return {"job_id": r[0], "job_status": r[1], "existing": True, "ingestion_version": VERSION}
        q.execute(
            f"INSERT INTO {TABLE}(job_id,organization_id,plant_id,actor_json,status,message,created_at,updated_at) VALUES({','.join([ph]*8)})",
            (jid, a["organization_id"], pid, json.dumps(a, separators=(",", ":")), "QUEUED", "Queued for direct universal plant knowledge ingestion.", t, t),
        )
    return {"job_id": jid, "job_status": "QUEUED", "existing": False, "ingestion_version": VERSION}

def claim():
    init_schema(); ph = p(); t = now()
    with store._connect() as c:
        q = c.cursor()
        q.execute(f"SELECT job_id,plant_id,organization_id,actor_json FROM {TABLE} WHERE status='QUEUED' ORDER BY created_at LIMIT 1")
        r = q.fetchone()
        if not r: return None
        jid, pid, org, raw = r
        a = raw if isinstance(raw, dict) else json.loads(raw or "{}")
        q.execute(f"UPDATE {TABLE} SET status={ph},message={ph},started_at={ph},updated_at={ph} WHERE job_id={ph} AND status='QUEUED'", ("RUNNING", "Direct ingestion execution started.", t, t, jid))
        if getattr(q, "rowcount", 1) != 1: return None
    return jid, pid, org, a

def process_one():
    job = claim()
    if not job:
        return {"processed": 0, "job_id": None, "status": "IDLE", "safety": dict(SAFETY)}
    jid, pid, org, a = job
    try:
        import anvi_plant_ingestion_runtime as runtime
        r = runtime.ingest_plant(pid, a)
        st = "COMPLETED" if r.get("status") == "OK" and not r.get("errors") else "COMPLETED_WITH_ERRORS"
        msg = f"Processed {r.get('documents_processed', 0)} documents and indexed {r.get('records_indexed', 0)} records."
    except Exception as e:
        r = {"status": "ERROR", "plant_id": pid, "message": str(e), "errors": [{"error": str(e)}], "safety": dict(SAFETY)}
        st = "FAILED"; msg = str(e)
    t = now(); ph = p()
    with store._connect() as c:
        c.cursor().execute(f"UPDATE {TABLE} SET status={ph},message={ph},result_json={ph},finished_at={ph},updated_at={ph} WHERE job_id={ph}", (st, msg, json.dumps(r, default=str), t, t, jid))
    # Keep the visible onboarding state synchronized with the actual result.
    try:
        with store._connect() as c:
            q = c.cursor(); target = "READY" if st == "COMPLETED" else ("INDEXING" if st == "COMPLETED_WITH_ERRORS" else "DATA_UPLOADED")
            q.execute(f"UPDATE anviqo_plant_onboarding SET status={ph},updated_at={ph} WHERE plant_id={ph} AND organization_id={ph}", (target, t, pid, org))
    except Exception:
        pass
    return {"processed": 1, "job_id": jid, "status": st, "result": r, "safety": dict(SAFETY), "ingestion_version": VERSION}

def register(app):
    init_schema()

    @app.post("/api/admin/onboarding/plant/<plant_id>/ingest", endpoint="anvi_clean_ingest_start")
    def start(plant_id):
        from flask import jsonify
        a = actor()
        if not ok(plant_id, a):
            return jsonify({"status": "FORBIDDEN", "message": "OWNER/ADMIN access to this plant is required"}), 403
        queued = enqueue(plant_id, a)
        # Reliable path: execute the newly queued job in this request. This removes
        # the dependency on a second Render service, polling race, or lost dispatch.
        if queued.get("job_status") == "QUEUED":
            result = process_one()
            return jsonify({**queued, **result, "mode": "DIRECT"}), 200
        return jsonify({**queued, "mode": "DIRECT_ALREADY_RUNNING"}), 202

    @app.get("/api/admin/onboarding/plant/<plant_id>/ingest/status", endpoint="anvi_clean_ingest_status")
    def status(plant_id):
        from flask import jsonify
        a = actor()
        if not ok(plant_id, a):
            return jsonify({"status": "FORBIDDEN", "message": "OWNER/ADMIN access to this plant is required"}), 403
        ph = p()
        with store._connect() as c:
            q = c.cursor(); q.execute(f"SELECT job_id,status,message,result_json,created_at,started_at,finished_at,updated_at FROM {TABLE} WHERE plant_id={ph} AND organization_id={ph} ORDER BY created_at DESC LIMIT 1", (plant_id, a["organization_id"]))
            r = q.fetchone()
        if not r:
            reconcile_legacy_ui(plant_id, a)
            return jsonify({"status": "NOT_STARTED", "job_status": "NOT_STARTED", "ingestion_version": VERSION})
        jid, st, msg, res, cr, ss, ff, up = r
        if isinstance(res, str):
            try: res = json.loads(res or "{}")
            except Exception: res = {}
        reconcile_legacy_ui(plant_id, a)
        return jsonify({"job_id": jid, "status": st, "job_status": st, "message": msg, "result": res or {}, "created_at": str(cr), "started_at": str(ss) if ss else None, "finished_at": str(ff) if ff else None, "updated_at": str(up) if up else None, "ingestion_version": VERSION})

    # Retained only as a compatibility fallback for the existing worker. The
    # onboarding button no longer depends on it.
    @app.post("/api/internal/ingestion/dispatch", endpoint="anvi_clean_ingest_dispatch")
    def dispatch():
        from flask import jsonify, request
        expected = os.environ.get("ANVI_INGESTION_DISPATCH_TOKEN", "").strip()
        if not expected or request.headers.get("X-ANVI-INGESTION-TOKEN", "").strip() != expected:
            return jsonify({"status": "FORBIDDEN", "message": "Invalid ingestion dispatch authorization"}), 403
        return jsonify(process_one())
