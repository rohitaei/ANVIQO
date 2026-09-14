"""Durable universal plant-data importer for ANVIQO.

The web process owns the durable queue fallback. This avoids making the
import path depend on a separately configured worker service. The existing
PostgreSQL tenant store remains the single source of truth.
"""
from __future__ import annotations
import csv, hashlib, io, json, re, threading, time, uuid, zipfile
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import anvi_tenant_store as store
from universal_onboarding import normalize_record, SAFETY

VERSION = "ANVIQO-DIRECT-PLANT-DATA-V1.4.10"
BATCH_SIZE = 250
JOB_TABLE = "anviqo_direct_import_jobs"
_LOCAL_WORKER_STARTED = False
_LOCAL_WORKER_THREAD = None
_LOCAL_WORKER_LOCK = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat()

def _p(): return store._placeholder()
def _nonempty(v): return v is not None and str(v).strip() != ""
def _key(v): return re.sub(r"[^a-z0-9]+", "", str(v or "").strip().lower())
def _header_score(row):
    known = {"tag","tagname","plctag","plctagname","externalid","assetid","area","service","description","iotype","plcaddress","panel","tb","jb","recordtype","entitytype"}
    return sum(1 for v in row if _key(v) in known)

def _matrix_records(sheet_name, rows):
    """Convert a worksheet iterator without materializing the whole sheet."""
    iterator = iter(rows); sample = []
    for _ in range(30):
        try: row = tuple(next(iterator))
        except StopIteration: break
        if any(_nonempty(v) for v in row): sample.append(row)
    if not sample: return
    hi = max(range(len(sample)), key=lambda i: _header_score(sample[i])); first = sample[hi]
    headers, seen = [], {}
    for i, v in enumerate(first):
        h = str(v).strip() if _nonempty(v) else "column_" + str(i + 1)
        k = _key(h); seen[k] = seen.get(k, 0) + 1; headers.append(h if seen[k] == 1 else h + "_" + str(seen[k]))
    def emit(row, idx):
        if not any(_nonempty(v) for v in row): return None
        rec = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        rec = {str(k).strip(): v for k, v in rec.items() if str(k).strip()}
        rec["external_id"] = str(rec.get("external_id") or rec.get("id") or rec.get("tag") or rec.get("asset_id") or rec.get("TAG") or hashlib.sha256((sheet_name + str(idx) + json.dumps(rec, sort_keys=True, default=str)).encode()).hexdigest()[:20])
        rec["source"] = sheet_name; rec["record_type"] = str(rec.get("record_type") or rec.get("entity_type") or rec.get("type") or "ASSET")
        return rec
    for offset, row in enumerate(sample[hi + 1:], start=hi + 2):
        rec = emit(row, offset)
        if rec is not None: yield rec
    idx = len(sample) + 1
    for row in iterator:
        rec = emit(tuple(row), idx); idx += 1
        if rec is not None: yield rec

def _xlsx_records(raw):
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(bytes(raw)), read_only=True, data_only=True)
    try:
        for ws in wb.worksheets: yield from _matrix_records(ws.title, ws.iter_rows(values_only=True))
    finally: wb.close()

def _xls_records(raw):
    import xlrd
    wb = xlrd.open_workbook(file_contents=bytes(raw), on_demand=True)
    try:
        for ws in wb.sheets(): yield from _matrix_records(ws.name, (ws.row_values(i) for i in range(ws.nrows)))
    finally: wb.release_resources()

def _records(filename, raw):
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""; blob = bytes(raw)
    is_xls = blob.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"); is_xlsx = blob.startswith(b"PK\x03\x04")
    if ext == "xls" or (not ext and is_xls) or (is_xls and ext != "xlsx"): yield from _xls_records(blob); return
    if ext == "xlsx" or is_xlsx: yield from _xlsx_records(blob); return
    if ext == "csv":
        for i, row in enumerate(csv.DictReader(io.StringIO(blob.decode("utf-8-sig", errors="replace")))):
            row = dict(row); row["external_id"] = str(row.get("external_id") or row.get("id") or row.get("tag") or row.get("asset_id") or hashlib.sha256((filename + str(i) + json.dumps(row, sort_keys=True, default=str)).encode()).hexdigest()[:20]); row["source"] = filename; row["record_type"] = str(row.get("record_type") or row.get("entity_type") or row.get("type") or "ASSET"); yield row
        return
    if ext == "json":
        data = json.loads(blob.decode("utf-8", errors="replace")); data = (data.get("records") or data.get("data") or [data]) if isinstance(data, dict) else data
        for i, row in enumerate(data if isinstance(data, list) else []):
            if isinstance(row, dict):
                row = dict(row); row["external_id"] = str(row.get("external_id") or row.get("id") or row.get("tag") or row.get("asset_id") or hashlib.sha256((filename + str(i) + json.dumps(row, sort_keys=True, default=str)).encode()).hexdigest()[:20]); row["source"] = filename; row["record_type"] = str(row.get("record_type") or row.get("entity_type") or row.get("type") or "ASSET"); yield row
        return
    text = ""
    if ext in {"txt", "log"}: text = blob.decode("utf-8-sig", errors="replace")
    elif ext == "docx":
        with zipfile.ZipFile(io.BytesIO(blob)) as z: xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        text = "\n".join(re.sub(r"<[^>]+>", " ", x).strip() for x in re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml) if x.strip())
    elif ext == "pdf":
        try:
            from pypdf import PdfReader
            text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(blob)).pages)
        except Exception: text = ""
    if text.strip():
        for i in range(0, len(text), 6000): yield {"external_id": hashlib.sha256((filename + str(i)).encode()).hexdigest()[:20], "name": filename, "record_type": "DOCUMENT", "source": filename, "metadata": {"content": text[i:i + 6000]}}

def _knowledge_schema():
    with store._connect() as conn:
        cur = conn.cursor()
        if store._is_sqlite():
            cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_knowledge (knowledge_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, document_id TEXT, record_type TEXT NOT NULL, external_id TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT '', service TEXT NOT NULL DEFAULT '', asset_type TEXT NOT NULL DEFAULT '', tag TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', metadata TEXT NOT NULL DEFAULT '{}', content TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, UNIQUE(plant_id,external_id,source))")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_knowledge (knowledge_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, document_id TEXT, record_type TEXT NOT NULL, external_id TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT '', service TEXT NOT NULL DEFAULT '', asset_type TEXT NOT NULL DEFAULT '', tag TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', metadata JSONB NOT NULL DEFAULT '{}'::jsonb, content TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
            cur.execute("ALTER TABLE anviqo_plant_knowledge ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT ''"); cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_anviqo_plant_knowledge_plant_external_source ON anviqo_plant_knowledge(plant_id,external_id,source)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_anviqo_plant_knowledge_plant ON anviqo_plant_knowledge(plant_id)")

def _job_schema():
    with store._connect() as conn:
        cur = conn.cursor()
        sql = ("CREATE TABLE IF NOT EXISTS " + JOB_TABLE + " (job_id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,plant_id TEXT NOT NULL,actor_json TEXT NOT NULL,status TEXT NOT NULL,message TEXT NOT NULL,result_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,started_at TEXT,finished_at TEXT,updated_at TEXT NOT NULL)" if store._is_sqlite() else "CREATE TABLE IF NOT EXISTS " + JOB_TABLE + " (job_id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,plant_id TEXT NOT NULL,actor_json JSONB NOT NULL,status TEXT NOT NULL,message TEXT NOT NULL,result_json JSONB NOT NULL DEFAULT '{}'::jsonb,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),started_at TIMESTAMPTZ,finished_at TIMESTAMPTZ,updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
        cur.execute(sql); cur.execute("CREATE INDEX IF NOT EXISTS idx_" + JOB_TABLE + "_plant ON " + JOB_TABLE + "(plant_id,organization_id,created_at)")

def _insert_batch(plant_id, org_id, document_id, digest, records):
    p = _p(); rows = []; errors = []
    for raw in records:
        try:
            n = normalize_record(raw, str(raw.get("record_type") or "ASSET")); item = asdict(n) if is_dataclass(n) else dict(n); meta = dict(item.get("metadata") or {}); meta.update(import_version=VERSION, document_sha256=digest); content = str(meta.pop("content", "") or ""); external_id = str(item.get("external_id", "")); source = str(item.get("source", "")); kid = "know_" + hashlib.sha256((plant_id + document_id + external_id + source).encode()).hexdigest()[:24]
            rows.append((kid, org_id, plant_id, document_id, item.get("record_type", "ASSET"), external_id, item.get("name", ""), item.get("area", ""), item.get("service", ""), item.get("asset_type", ""), item.get("tag", ""), item.get("parent_id", ""), source, json.dumps(meta, default=str), content))
        except Exception as exc: errors.append(str(exc))
    if not rows: return 0, errors
    with store._connect() as conn:
        cur = conn.cursor(); ph = [p] * 15
        if not store._is_sqlite(): ph[13] = p + "::jsonb"
        if store._is_sqlite():
            sql = "INSERT OR REPLACE INTO anviqo_plant_knowledge(knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content,created_at) VALUES(" + ",".join(ph) + "," + p + ")"; cur.executemany(sql, [r + (_now(),) for r in rows])
        else:
            sql = "INSERT INTO anviqo_plant_knowledge(knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content) VALUES(" + ",".join(ph) + ") ON CONFLICT(plant_id,external_id,source) DO UPDATE SET organization_id=EXCLUDED.organization_id,document_id=EXCLUDED.document_id,name=EXCLUDED.name,area=EXCLUDED.area,service=EXCLUDED.service,asset_type=EXCLUDED.asset_type,tag=EXCLUDED.tag,parent_id=EXCLUDED.parent_id,metadata=EXCLUDED.metadata,content=EXCLUDED.content"; cur.executemany(sql, rows)
    return len(rows), errors

def import_plant_data(plant_id, actor):
    if not actor.get("user_id") or not actor.get("organization_id") or actor.get("role") not in {"OWNER", "ADMIN"}: raise PermissionError("OWNER/ADMIN access to this plant is required")
    p = _p(); _knowledge_schema()
    with store._connect() as conn:
        cur = conn.cursor(); cur.execute("SELECT 1 FROM anviqo_plants WHERE plant_id=" + p + " AND organization_id=" + p + " AND status='ACTIVE'", (plant_id, actor["organization_id"]))
        if not cur.fetchone(): raise PermissionError("Plant is not active in this organization")
        cur.execute("SELECT document_id,filename,sha256 FROM anviqo_plant_documents WHERE plant_id=" + p + " AND organization_id=" + p + " ORDER BY created_at", (plant_id, actor["organization_id"])); docs = cur.fetchall()
    total = 0; documents = 0; errors = []
    for document_id, filename, digest in docs:
        try:
            with store._connect() as conn:
                cur = conn.cursor(); cur.execute("SELECT content FROM anviqo_plant_documents WHERE document_id=" + p + " AND plant_id=" + p + " AND organization_id=" + p, (document_id, plant_id, actor["organization_id"])); row = cur.fetchone()
            if not row: raise RuntimeError("Document content not found")
            raw = bytes(row[0]); batch = []
            for rec in _records(filename, raw):
                batch.append(rec)
                if len(batch) >= BATCH_SIZE:
                    a, e = _insert_batch(plant_id, actor["organization_id"], document_id, digest, batch); total += a; errors.extend({"filename": filename, "error": x} for x in e); print(f"ANVIQO_IMPORT_PROGRESS file={filename} records={total} errors={len(errors)}", flush=True); batch = []
            if batch:
                a, e = _insert_batch(plant_id, actor["organization_id"], document_id, digest, batch); total += a; errors.extend({"filename": filename, "error": x} for x in e)
            documents += 1
        except Exception as exc: errors.append({"filename": filename, "error": str(exc)})
    status = "READY" if total > 0 and not errors else ("BLOCKED" if errors and not total else ("READY" if total > 0 else "DATA_UPLOADED"))
    with store._connect() as conn: conn.cursor().execute("UPDATE anviqo_plant_onboarding SET status=" + p + ",updated_at=" + p + " WHERE plant_id=" + p + " AND organization_id=" + p, (status, _now(), plant_id, actor["organization_id"]))
    try: store.record_audit(actor, "IMPORT_PLANT_DATA", "PLANT", plant_id, {"documents": documents, "records": total, "errors": len(errors), "version": VERSION})
    except Exception: pass
    return {"status": "OK" if total > 0 else "NO_KNOWLEDGE_CREATED", "plant_id": plant_id, "documents_processed": documents, "records_available_to_anvi": total, "errors": errors[:100], "error_count": len(errors), "import_version": VERSION, "mode": "WEB_LOCAL_ASYNC", "message": "Imported knowledge successfully" if total > 0 else ("Documents were found but produced zero normalized knowledge records. See errors for the exact document/parser/database reason." if errors else "Documents were found but the parser produced zero records. Check the uploaded file format/content."), "safety": dict(SAFETY)}

def enqueue_import(plant_id, actor):
    if not actor.get("user_id") or not actor.get("organization_id") or actor.get("role") not in {"OWNER", "ADMIN"}: raise PermissionError("OWNER/ADMIN access to this plant is required")
    _job_schema(); p = _p(); now = _now()
    with store._connect() as conn:
        cur = conn.cursor(); cur.execute("SELECT 1 FROM anviqo_plants WHERE plant_id=" + p + " AND organization_id=" + p + " AND status='ACTIVE' LIMIT 1", (plant_id, actor["organization_id"]))
        if not cur.fetchone(): raise PermissionError("Plant is not active in this organization")
        cur.execute("SELECT job_id,status FROM " + JOB_TABLE + " WHERE plant_id=" + p + " AND organization_id=" + p + " AND status IN('QUEUED','RUNNING') ORDER BY created_at DESC LIMIT 1", (plant_id, actor["organization_id"])); existing = cur.fetchone()
        if existing: return {"job_id": existing[0], "job_status": existing[1], "existing": True, "mode": "WEB_LOCAL_ASYNC", "import_version": VERSION}
        jid = "imp_" + uuid.uuid4().hex; cur.execute("INSERT INTO " + JOB_TABLE + "(job_id,organization_id,plant_id,actor_json,status,message,created_at,updated_at) VALUES(" + ",".join([p] * 8) + ")", (jid, actor["organization_id"], plant_id, json.dumps(actor, separators=(",", ":")), "QUEUED", "Queued for background plant-data import.", now, now))
    _start_local_worker(); return {"job_id": jid, "job_status": "QUEUED", "existing": False, "mode": "WEB_LOCAL_ASYNC", "import_version": VERSION}

def _claim_job():
    p = _p(); _job_schema()
    with store._connect() as conn:
        cur = conn.cursor()
        if not store._is_sqlite():
            cur.execute("UPDATE " + JOB_TABLE + " SET status='QUEUED',message='Recovered abandoned import after worker restart.',started_at=NULL,updated_at=NOW() WHERE status='RUNNING' AND updated_at < NOW() - INTERVAL '2 minutes'")
        else:
            cur.execute("UPDATE " + JOB_TABLE + " SET status='QUEUED',message='Recovered abandoned import after worker restart.',started_at=NULL,updated_at=? WHERE status='RUNNING' AND updated_at < ?", (_now(), _now()))
        if store._is_sqlite():
            cur.execute("SELECT job_id,organization_id,plant_id,actor_json FROM " + JOB_TABLE + " WHERE status='QUEUED' ORDER BY created_at LIMIT 1"); row = cur.fetchone()
            if not row: return None
            cur.execute("UPDATE " + JOB_TABLE + " SET status='RUNNING',message='Import running in ANVIQO web process.',started_at=" + p + ",updated_at=" + p + " WHERE job_id=" + p + " AND status='QUEUED'", (_now(), _now(), row[0]))
            if getattr(cur, "rowcount", 1) != 1: return None
        else:
            cur.execute("SELECT job_id,organization_id,plant_id,actor_json FROM " + JOB_TABLE + " WHERE status='QUEUED' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1"); row = cur.fetchone()
            if not row: return None
            cur.execute("UPDATE " + JOB_TABLE + " SET status='RUNNING',message='Import running in ANVIQO web process.',started_at=NOW(),updated_at=NOW() WHERE job_id=" + p + " AND status='QUEUED'", (row[0],))
        return row

def _touch_job(job_id):
    p = _p()
    try:
        with store._connect() as conn:
            if store._is_sqlite():
                conn.cursor().execute("UPDATE " + JOB_TABLE + " SET updated_at=? WHERE job_id=" + p, (_now(), job_id))
            else:
                conn.cursor().execute("UPDATE " + JOB_TABLE + " SET updated_at=NOW() WHERE job_id=" + p, (job_id,))
    except Exception:
        pass

def _finish_job(job_id, status, result, message):
    p = _p()
    with store._connect() as conn: conn.cursor().execute("UPDATE " + JOB_TABLE + " SET status=" + p + ",message=" + p + ",result_json=" + (p + "::jsonb" if not store._is_sqlite() else p) + ",finished_at=" + ("NOW()" if not store._is_sqlite() else p) + ",updated_at=" + ("NOW()" if not store._is_sqlite() else p) + " WHERE job_id=" + p, (status, message, json.dumps(result, default=str), *([_now(), _now()] if store._is_sqlite() else []), job_id))

def _local_worker_loop():
    print("ANVIQO_IMPORT_WORKER started", flush=True)
    while True:
        try:
            job = _claim_job()
            if not job: time.sleep(2); continue
            job_id, org_id, plant_id, actor_json = job; print(f"ANVIQO_IMPORT_WORKER claimed job={job_id} plant={plant_id}", flush=True)
            actor = json.loads(actor_json) if isinstance(actor_json, str) else dict(actor_json)
            try:
                print(f"ANVIQO_IMPORT_WORKER processing job={job_id} plant={plant_id}", flush=True)
                hb_stop = threading.Event()
                def _hb():
                    while not hb_stop.wait(20):
                        _touch_job(job_id)
                        print(f"ANVIQO_IMPORT_WORKER heartbeat job={job_id}", flush=True)
                hb = threading.Thread(target=_hb, name="anviqo-import-heartbeat", daemon=True); hb.start()
                try:
                    result = import_plant_data(plant_id, actor)
                finally:
                    hb_stop.set(); hb.join(timeout=2); _touch_job(job_id)
                _finish_job(job_id, "SUCCEEDED" if result.get("records_available_to_anvi", 0) > 0 else "FAILED", result, result.get("message", "Import finished.")); print(f"ANVIQO_IMPORT_WORKER finished job={job_id} status={result.get('status')} records={result.get('records_available_to_anvi', 0)} errors={result.get('error_count', 0)}", flush=True)
            except Exception as exc:
                print(f"ANVIQO_IMPORT_WORKER failed job={job_id}: {exc!r}", flush=True)
                try: _finish_job(job_id, "FAILED", {"status": "ERROR", "error": str(exc), "plant_id": plant_id, "import_version": VERSION}, str(exc))
                except Exception as finish_exc: print(f"ANVIQO_IMPORT_WORKER could not mark job failed job={job_id}: {finish_exc!r}", flush=True)
        except Exception: time.sleep(3)

def _start_local_worker():
    global _LOCAL_WORKER_STARTED, _LOCAL_WORKER_THREAD
    with _LOCAL_WORKER_LOCK:
        if _LOCAL_WORKER_THREAD is not None and _LOCAL_WORKER_THREAD.is_alive(): return
        _LOCAL_WORKER_STARTED = True; _LOCAL_WORKER_THREAD = threading.Thread(target=_local_worker_loop, name="anviqo-web-import-worker", daemon=True); _LOCAL_WORKER_THREAD.start(); print("ANVIQO_IMPORT_WORKER thread launched", flush=True)

def get_import_status(plant_id, actor):
    _job_schema(); p = _p()
    with store._connect() as conn:
        cur = conn.cursor(); cur.execute("SELECT job_id,status,message,result_json,created_at,started_at,finished_at,updated_at FROM " + JOB_TABLE + " WHERE plant_id=" + p + " AND organization_id=" + p + " ORDER BY created_at DESC LIMIT 1", (plant_id, actor["organization_id"])); r = cur.fetchone()
    if not r: return {"status": "NOT_STARTED", "job_status": "NOT_STARTED", "plant_id": plant_id, "mode": "WEB_LOCAL_ASYNC", "import_version": VERSION}
    jid, st, msg, res, cr, ss, ff, up = r
    if isinstance(res, str):
        try: res = json.loads(res or "{}")
        except Exception: res = {}
    return {"job_id": jid, "status": st, "job_status": st, "message": msg, "result": res or {}, "created_at": str(cr), "started_at": str(ss) if ss else None, "finished_at": str(ff) if ff else None, "updated_at": str(up) if up else None, "plant_id": plant_id, "mode": "WEB_LOCAL_ASYNC", "import_version": VERSION}

def register(app):
    from flask import jsonify, session
    _start_local_worker()
    @app.post("/api/admin/onboarding/plant/<plant_id>/import")
    def import_route(plant_id):
        actor = {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}
        try: return jsonify(enqueue_import(plant_id, actor)), 200
        except Exception as exc: return jsonify({"status": "ERROR", "message": str(exc), "mode": "WEB_LOCAL_ASYNC", "safety": dict(SAFETY)}), 400
    @app.get("/api/admin/onboarding/plant/<plant_id>/import-status")
    def import_status_route(plant_id):
        actor = {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}
        if not actor.get("user_id") or actor.get("role") not in {"OWNER", "ADMIN"}: return jsonify({"status": "FORBIDDEN"}), 403
        try: return jsonify(get_import_status(plant_id, actor)), 200
        except Exception as exc: return jsonify({"status": "ERROR", "message": str(exc)}), 400
    @app.get("/api/admin/onboarding/plant/<plant_id>/knowledge-summary")
    def knowledge_summary(plant_id):
        actor = {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}
        if not actor.get("user_id") or actor.get("role") not in {"OWNER", "ADMIN"}: return jsonify({"status": "FORBIDDEN"}), 403
        p = _p()
        with store._connect() as conn:
            cur = conn.cursor(); cur.execute("SELECT record_type,COUNT(*) FROM anviqo_plant_knowledge WHERE plant_id=" + p + " AND organization_id=" + p + " GROUP BY record_type ORDER BY COUNT(*) DESC", (plant_id, actor["organization_id"])); groups = [{"record_type": r[0], "count": r[1]} for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*) FROM anviqo_plant_knowledge WHERE plant_id=" + p + " AND organization_id=" + p, (plant_id, actor["organization_id"])); total = cur.fetchone()[0]
        return jsonify({"status": "OK", "plant_id": plant_id, "total_records": total, "by_type": groups, "mode": "WEB_LOCAL_ASYNC", "safety": dict(SAFETY)})
    return app

__all__ = ["import_plant_data", "enqueue_import", "get_import_status", "_job_schema", "register"]
