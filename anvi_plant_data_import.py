"""ANVIQO clean plant-data import path.

This is deliberately NOT a job/queue/worker system. It imports the files
already stored for a selected tenant plant directly into the universal plant
knowledge store. Frozen V5 intelligence and PLC/SCADA boundaries are untouched.
Principle: CHANGE DATA, NOT CODE.
"""
from __future__ import annotations

import csv, hashlib, io, json, re, zipfile
from datetime import datetime, timezone
import anvi_tenant_store as store
from universal_onboarding import build_onboarding_package, SAFETY

VERSION = "ANVIQO-DIRECT-PLANT-DATA-V1"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _p():
    return store._placeholder()


def _xlsx_records(raw):
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            rows = ws.iter_rows(values_only=True)
            try:
                first = next(rows)
            except StopIteration:
                continue
            headers = [str(v).strip() if v is not None and str(v).strip() else f"column_{i+1}" for i, v in enumerate(first)]
            for idx, row in enumerate(rows, start=2):
                if not any(v is not None and str(v).strip() for v in row):
                    continue
                rec = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                rec = {str(k).strip(): v for k, v in rec.items() if str(k).strip()}
                rec["external_id"] = str(rec.get("external_id") or rec.get("id") or rec.get("tag") or rec.get("asset_id") or hashlib.sha256((ws.title + str(idx) + json.dumps(rec, sort_keys=True, default=str)).encode()).hexdigest()[:20])
                rec["source"] = ws.title
                rec["record_type"] = str(rec.get("record_type") or rec.get("entity_type") or rec.get("type") or "ASSET")
                yield rec
    finally:
        wb.close()


def _text(raw, ext):
    if ext in {"txt", "log", "csv"}:
        return raw.decode("utf-8-sig", errors="replace")
    if ext == "docx":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        return "\n".join(re.sub(r"<[^>]+>", " ", x).strip() for x in re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml) if x.strip())
    if ext == "pdf":
        try:
            from pypdf import PdfReader
            return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages)
        except Exception:
            return ""
    return ""


def _records(filename, raw):
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "xlsx":
        return list(_xlsx_records(raw))
    if ext == "csv":
        out = []
        for i, row in enumerate(csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="replace")))):
            row = dict(row)
            row["external_id"] = str(row.get("external_id") or row.get("id") or row.get("tag") or row.get("asset_id") or hashlib.sha256((filename + str(i) + json.dumps(row, sort_keys=True)).encode()).hexdigest()[:20])
            row["source"] = filename
            row["record_type"] = str(row.get("record_type") or row.get("entity_type") or row.get("type") or "ASSET")
            out.append(row)
        return out
    if ext == "json":
        data = json.loads(raw.decode("utf-8", errors="replace"))
        if isinstance(data, dict):
            data = data.get("records") or data.get("data") or [data]
        out = []
        for i, row in enumerate(data if isinstance(data, list) else []):
            if not isinstance(row, dict):
                continue
            row = dict(row)
            row["external_id"] = str(row.get("external_id") or row.get("id") or row.get("tag") or row.get("asset_id") or hashlib.sha256((filename + str(i) + json.dumps(row, sort_keys=True)).encode()).hexdigest()[:20])
            row["source"] = filename
            row["record_type"] = str(row.get("record_type") or row.get("entity_type") or row.get("type") or "ASSET")
            out.append(row)
        return out
    text = _text(raw, ext)
    if not text.strip():
        return []
    return [{"external_id": hashlib.sha256((filename + str(i)).encode()).hexdigest()[:20], "name": filename, "record_type": "DOCUMENT", "source": filename, "metadata": {"content": chunk}} for i, chunk in enumerate(text[i:i+6000] for i in range(0, len(text), 6000))]


def _knowledge_schema():
    with store._connect() as conn:
        cur = conn.cursor()
        p = _p()
        if store._is_sqlite():
            cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_knowledge (knowledge_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, document_id TEXT, record_type TEXT NOT NULL, external_id TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT '', service TEXT NOT NULL DEFAULT '', asset_type TEXT NOT NULL DEFAULT '', tag TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', metadata TEXT NOT NULL DEFAULT '{}', content TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, UNIQUE(plant_id,external_id,source))")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS anviqo_plant_knowledge (knowledge_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, document_id TEXT, record_type TEXT NOT NULL, external_id TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', area TEXT NOT NULL DEFAULT '', service TEXT NOT NULL DEFAULT '', asset_type TEXT NOT NULL DEFAULT '', tag TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT '', metadata JSONB NOT NULL DEFAULT '{}'::jsonb, content TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), UNIQUE(plant_id,external_id,source))")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_anviqo_plant_knowledge_plant ON anviqo_plant_knowledge(plant_id)")


def _insert(plant_id, org_id, document_id, digest, rec):
    normalized = build_onboarding_package({"organization_id": org_id, "plant_id": plant_id}, [rec]).get("records", [])
    p = _p(); rows = []
    for item in normalized:
        meta = dict(item.get("metadata") or {})
        meta["import_version"] = VERSION
        meta["document_sha256"] = digest
        content = str(meta.pop("content", "") or "")
        kid = "know_" + hashlib.sha256((plant_id + document_id + str(item.get("external_id", "")) + str(item.get("source", ""))).encode()).hexdigest()[:24]
        rows.append((kid, org_id, plant_id, document_id, item.get("record_type", "ASSET"), str(item.get("external_id", "")), item.get("name", ""), item.get("area", ""), item.get("service", ""), item.get("asset_type", ""), item.get("tag", ""), item.get("parent_id", ""), item.get("source", ""), json.dumps(meta), content))
    if not rows:
        return 0
    with store._connect() as conn:
        cur = conn.cursor()
        if store._is_sqlite():
            cur.executemany(f"INSERT OR REPLACE INTO anviqo_plant_knowledge(knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content,created_at) VALUES({','.join([p]*15)},{p})", [r + (_now(),) for r in rows])
        else:
            cur.executemany(f"INSERT INTO anviqo_plant_knowledge(knowledge_id,organization_id,plant_id,document_id,record_type,external_id,name,area,service,asset_type,tag,parent_id,source,metadata,content) VALUES({','.join([p]*15)}) ON CONFLICT(plant_id,external_id,source) DO UPDATE SET name=EXCLUDED.name,area=EXCLUDED.area,service=EXCLUDED.service,asset_type=EXCLUDED.asset_type,tag=EXCLUDED.tag,metadata=EXCLUDED.metadata,content=EXCLUDED.content", rows)
    return len(rows)


def import_plant_data(plant_id, actor):
    if not actor.get("user_id") or actor.get("role") not in {"OWNER", "ADMIN"}:
        raise PermissionError("OWNER/ADMIN access to this plant is required")
    p = _p()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM anviqo_plants WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE'", (plant_id, actor["organization_id"]))
        if not cur.fetchone():
            raise PermissionError("Plant is not active in this organization")
        cur.execute(f"SELECT document_id,filename,content,sha256 FROM anviqo_plant_documents WHERE plant_id={p} AND organization_id={p} ORDER BY created_at", (plant_id, actor["organization_id"]))
        docs = cur.fetchall()
    _knowledge_schema()
    total = documents = 0; errors = []
    for document_id, filename, raw, digest in docs:
        try:
            records = _records(filename, bytes(raw))
            for rec in records:
                total += _insert(plant_id, actor["organization_id"], document_id, digest, rec)
            documents += 1
        except Exception as exc:
            errors.append({"filename": filename, "error": str(exc)})
    status = "READY" if documents and not errors else "BLOCKED" if errors else "DATA_UPLOADED"
    with store._connect() as conn:
        conn.cursor().execute(f"UPDATE anviqo_plant_onboarding SET status={p},updated_at={p} WHERE plant_id={p} AND organization_id={p}", (status, _now(), plant_id, actor["organization_id"]))
    try:
        store.record_audit(actor, "IMPORT_PLANT_DATA", "PLANT", plant_id, {"documents": documents, "records": total, "errors": len(errors), "version": VERSION})
    except Exception:
        pass
    return {"status": "OK" if not errors else "COMPLETED_WITH_ERRORS", "plant_id": plant_id, "documents_processed": documents, "records_available_to_anvi": total, "errors": errors, "import_version": VERSION, "mode": "DIRECT", "safety": dict(SAFETY)}


def register(app):
    from flask import jsonify, request
    from flask import session

    @app.post("/api/admin/onboarding/plant/<plant_id>/import")
    def import_route(plant_id):
        actor = {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}
        try:
            result = import_plant_data(plant_id, actor)
            return jsonify(result), 200
        except Exception as exc:
            return jsonify({"status": "ERROR", "message": str(exc), "mode": "DIRECT", "safety": dict(SAFETY)}), 400

    @app.get("/api/admin/onboarding/plant/<plant_id>/knowledge-summary")
    def knowledge_summary(plant_id):
        actor = {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}
        if not actor.get("user_id") or actor.get("role") not in {"OWNER", "ADMIN"}:
            return jsonify({"status": "FORBIDDEN"}), 403
        p = _p(); _knowledge_schema()
        with store._connect() as conn:
            cur = conn.cursor(); cur.execute(f"SELECT record_type,COUNT(*) FROM anviqo_plant_knowledge WHERE plant_id={p} AND organization_id={p} GROUP BY record_type ORDER BY COUNT(*) DESC", (plant_id,)); groups = [{"record_type": r[0], "count": r[1]} for r in cur.fetchall()]
            cur.execute(f"SELECT COUNT(*) FROM anviqo_plant_knowledge WHERE plant_id={p} AND organization_id={p}", (plant_id,)); total = cur.fetchone()[0]
        return jsonify({"status": "OK", "plant_id": plant_id, "total_records": total, "by_type": groups, "mode": "DIRECT", "safety": dict(SAFETY)})

    return app


__all__ = ["import_plant_data", "register"]
