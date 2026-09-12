"""ANVIQO Universal Plant Onboarding foundation.

This layer is intentionally separate from frozen V5 intelligence. It stores
plant onboarding metadata and source documents, scoped to the owner's/admin's
organization. Future ingestion workers can consume these sources without
creating plant-specific reasoning code.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from flask import jsonify, request, Response

import anvi_tenant_store as store
from phase6_enterprise_runtime import app

_ALLOWED_EXT = {"pdf", "docx", "xlsx", "xls", "csv", "json", "txt", "png", "jpg", "jpeg"}
_MAX_BYTES = int(os.getenv("ANVIQO_ONBOARDING_MAX_BYTES", str(25 * 1024 * 1024)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _placeholder() -> str:
    return store._placeholder()


def _actor() -> dict:
    from flask import session
    return {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}


def _admin() -> bool:
    a = _actor()
    return bool(a["user_id"] and a["organization_id"] and a["role"] in {"OWNER", "ADMIN"})


def _plant_ok(plant_id: str) -> bool:
    a = _actor()
    if not _admin() or not plant_id: return False
    p = _placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM anviqo_plants WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE' LIMIT 1", (plant_id, a["organization_id"]))
        return cur.fetchone() is not None


def init_schema() -> None:
    if not store.enabled(): return
    with store._connect() as conn:
        cur = conn.cursor()
        if store._is_sqlite():
            cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_onboarding (plant_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, industry TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'CREATED', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
            cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_documents (document_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, filename TEXT NOT NULL, content_type TEXT NOT NULL DEFAULT 'application/octet-stream', size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, content BLOB NOT NULL, uploaded_by TEXT, created_at TEXT NOT NULL, UNIQUE(plant_id, sha256))")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_onboarding (plant_id TEXT PRIMARY KEY REFERENCES anviqo_plants(plant_id), organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), industry TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'CREATED', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())")
            cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_documents (document_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), plant_id TEXT NOT NULL REFERENCES anviqo_plants(plant_id), filename TEXT NOT NULL, content_type TEXT NOT NULL DEFAULT 'application/octet-stream', size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL, content BYTEA NOT NULL, uploaded_by TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(plant_id, sha256))")


def ensure_plant(plant_id: str) -> None:
    init_schema(); a = _actor(); p = _placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT plant_id FROM anviqo_plant_onboarding WHERE plant_id={p}", (plant_id,))
        if cur.fetchone(): return
        cur.execute(f"INSERT INTO anviqo_plant_onboarding(plant_id,organization_id,created_at,updated_at) VALUES({p},{p},{p},{p})", (plant_id, a["organization_id"], _now(), _now()))


def _reconcile_ingestion_state(plant_id: str) -> None:
    """Never let a historical INDEXING flag outlive its durable ingestion job.

    The onboarding page reads this endpoint. The durable V2 queue is therefore
    the source of truth for whether ingestion is actually active. This also
    heals legacy INDEXING rows left by the pre-V2 daemon-thread path.
    """
    a = _actor(); p = _placeholder(); active = {"QUEUED", "RUNNING"}
    try:
        with store._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT status FROM anviqo_plant_ingestion_jobs WHERE plant_id={p} AND organization_id={p} ORDER BY created_at DESC LIMIT 1", (plant_id, a["organization_id"]))
            row = cur.fetchone()
            if row and str(row[0]).upper() in active:
                return
            cur.execute(f"SELECT status FROM anviqo_plant_onboarding WHERE plant_id={p} AND organization_id={p}", (plant_id, a["organization_id"]))
            current = cur.fetchone()
            if current and str(current[0]).upper() == "INDEXING":
                cur.execute(f"UPDATE anviqo_plant_onboarding SET status='DATA_UPLOADED',updated_at={p} WHERE plant_id={p} AND organization_id={p}", (_now(), plant_id, a["organization_id"]))
    except Exception:
        # Status reconciliation must never break onboarding reads.
        pass


@app.get("/admin/onboarding")
def onboarding_page():
    if not _admin(): return Response("ANVIQO onboarding requires OWNER/ADMIN access", status=403, mimetype="text/plain")
    html = Path(__file__).with_name("anvi_universal_onboarding.html")
    if not html.is_file(): return Response("Onboarding page unavailable", status=500, mimetype="text/plain")
    return Response(html.read_text(encoding="utf-8"), status=200, mimetype="text/html")


@app.get("/api/admin/onboarding/plant/<plant_id>")
def onboarding_status(plant_id: str):
    if not _plant_ok(plant_id): return jsonify({"status": "FORBIDDEN"}), 403
    ensure_plant(plant_id)
    _reconcile_ingestion_state(plant_id)
    p = _placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT p.name,p.slug,o.industry,o.location,o.description,o.status,o.updated_at FROM anviqo_plants p LEFT JOIN anviqo_plant_onboarding o ON o.plant_id=p.plant_id WHERE p.plant_id={p}", (plant_id,))
        row = cur.fetchone()
        cur.execute(f"SELECT document_id,filename,content_type,size_bytes,sha256,created_at FROM anviqo_plant_documents WHERE plant_id={p} ORDER BY created_at DESC", (plant_id,))
        docs = [dict(r) if hasattr(r, "keys") else {"document_id": r[0], "filename": r[1], "content_type": r[2], "size_bytes": r[3], "sha256": r[4], "created_at": r[5]} for r in cur.fetchall()]
    keys = ["name", "slug", "industry", "location", "description", "status", "updated_at"]
    plant = dict(zip(keys, row)) if row else {}
    return jsonify({"status": "OK", "plant": plant, "documents": docs, "governance": {"v5_intelligence_modified": False, "plc_write": False, "scada_control": False, "human_decision_required": True}})


@app.post("/api/admin/onboarding/plant/<plant_id>/profile")
def update_onboarding_profile(plant_id: str):
    if not _plant_ok(plant_id): return jsonify({"status": "FORBIDDEN"}), 403
    ensure_plant(plant_id); body = request.get_json(silent=True) or {}
    industry = str(body.get("industry", "")).strip(); location = str(body.get("location", "")).strip(); description = str(body.get("description", "")).strip(); status = str(body.get("status", "CREATED")).upper().strip()
    allowed_status = {"CREATED", "DATA_UPLOADED", "INDEXING", "READY", "BLOCKED"}
    if status not in allowed_status: return jsonify({"status": "INVALID", "message": "Unsupported onboarding status"}), 400
    p = _placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE anviqo_plant_onboarding SET industry={p},location={p},description={p},status={p},updated_at={p} WHERE plant_id={p}", (industry,location,description,status,_now(),plant_id))
    try: store.record_audit(_actor(), "UPDATE_ONBOARDING", "PLANT", plant_id, {"status": status})
    except Exception: pass
    return jsonify({"status": "OK", "plant_id": plant_id, "onboarding_status": status})


@app.post("/api/admin/onboarding/plant/<plant_id>/documents")
def upload_onboarding_document(plant_id: str):
    if not _plant_ok(plant_id): return jsonify({"status": "FORBIDDEN"}), 403
    init_schema()
    uploaded = request.files.getlist("files")
    if not uploaded: return jsonify({"status": "INVALID", "message": "No files supplied"}), 400
    a = _actor(); p = _placeholder(); results = []
    for f in uploaded:
        filename = (f.filename or "").strip().replace("\\", "/").split("/")[-1]
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if not filename or ext not in _ALLOWED_EXT: return jsonify({"status": "INVALID", "message": f"Unsupported file type: {filename}"}), 400
        content = f.read()
        if len(content) > _MAX_BYTES: return jsonify({"status": "INVALID", "message": f"File too large: {filename}"}), 413
        digest = hashlib.sha256(content).hexdigest(); document_id = "doc_" + uuid.uuid4().hex
        try:
            with store._connect() as conn:
                cur = conn.cursor()
                if store._is_sqlite():
                    cur.execute(f"INSERT OR IGNORE INTO anviqo_plant_documents(document_id,organization_id,plant_id,filename,content_type,size_bytes,sha256,content,uploaded_by,created_at) VALUES({p},{p},{p},{p},{p},{p},{p},{p},{p},{p})", (document_id,a["organization_id"],plant_id,filename,f.content_type or "application/octet-stream",len(content),digest,content,a["username"],_now()))
                else:
                    cur.execute(f"INSERT INTO anviqo_plant_documents(document_id,organization_id,plant_id,filename,content_type,size_bytes,sha256,content,uploaded_by) VALUES({p},{p},{p},{p},{p},{p},{p},{p},{p}) ON CONFLICT(plant_id,sha256) DO NOTHING", (document_id,a["organization_id"],plant_id,filename,f.content_type or "application/octet-stream",len(content),digest,content,a["username"]))
            results.append({"filename": filename, "size_bytes": len(content), "sha256": digest})
        except Exception as exc: return jsonify({"status": "ERROR", "message": str(exc)}), 400
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE anviqo_plant_onboarding SET status='DATA_UPLOADED',updated_at={p} WHERE plant_id={p}", (_now(), plant_id))
    try: store.record_audit(a, "UPLOAD_PLANT_DOCUMENT", "PLANT", plant_id, {"documents": [r["filename"] for r in results]})
    except Exception: pass
    return jsonify({"status": "OK", "plant_id": plant_id, "documents": results, "message": "Source documents stored for plant-scoped onboarding."}), 201


init_schema()
