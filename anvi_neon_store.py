import os
import json

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

def neon_enabled():
    return bool(DATABASE_URL)

def _connect():
    import psycopg
    return psycopg.connect(DATABASE_URL)

def _exec(sql, params=(), fetch=False):
    conn=_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows=cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()

def init_neon():
    if not neon_enabled():
        return False

    statements=[
    """
    CREATE TABLE IF NOT EXISTS anviqo_equipment(
        tag TEXT PRIMARY KEY,
        payload JSONB NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS anviqo_registered_spares(
        spare_id TEXT PRIMARY KEY,
        equipment_tag TEXT,
        payload JSONB NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS anviqo_registration_audit(
        id BIGSERIAL PRIMARY KEY,
        event JSONB NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS anviqo_plant_memory(
        memory_id TEXT PRIMARY KEY,
        tag TEXT,
        equipment TEXT,
        payload JSONB NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS anviqo_field_reports(
        report_id TEXT PRIMARY KEY,
        tag TEXT,
        equipment TEXT,
        payload JSONB NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS anviqo_critical_spares(
        spare_key TEXT PRIMARY KEY,
        tag TEXT,
        payload JSONB NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS anviqo_spare_transactions(
        id BIGSERIAL PRIMARY KEY,
        tag TEXT,
        action TEXT,
        quantity INTEGER,
        before_qty INTEGER,
        after_qty INTEGER,
        payload JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """
    ]

    conn=_connect()
    try:
        with conn.cursor() as cur:
            for sql in statements:
                cur.execute(sql)
        conn.commit()
        return True
    finally:
        conn.close()

def _json(v):
    return json.dumps(v, ensure_ascii=False)

def upsert_equipment(record):
    if not neon_enabled(): return False
    init_neon()
    tag=str(record.get("tag","")).strip()
    if not tag: return False
    _exec("""
      INSERT INTO anviqo_equipment(tag,payload)
      VALUES(%s,%s::jsonb)
      ON CONFLICT(tag) DO UPDATE
      SET payload=EXCLUDED.payload, updated_at=NOW()
    """,(tag,_json(record)))
    return True

def get_equipment(tag=""):
    if not neon_enabled(): return []
    init_neon()
    rows=_exec(
      "SELECT payload FROM anviqo_equipment WHERE tag=%s",
      (str(tag).strip(),), True)
    return [r[0] for r in rows]

def upsert_registered_spare(record):
    if not neon_enabled(): return False
    init_neon()
    sid=str(record.get("spare_id","")).strip()
    if not sid: return False
    _exec("""
      INSERT INTO anviqo_registered_spares(spare_id,equipment_tag,payload)
      VALUES(%s,%s,%s::jsonb)
      ON CONFLICT(spare_id) DO UPDATE
      SET equipment_tag=EXCLUDED.equipment_tag,
          payload=EXCLUDED.payload, updated_at=NOW()
    """,(sid,str(record.get("equipment_tag","")),_json(record)))
    return True

def get_registered_spares(tag=""):
    if not neon_enabled(): return []
    init_neon()
    rows=_exec(
      "SELECT payload FROM anviqo_registered_spares WHERE equipment_tag=%s",
      (str(tag).strip(),), True)
    return [r[0] for r in rows]

def audit(event):
    if not neon_enabled(): return False
    init_neon()
    _exec(
      "INSERT INTO anviqo_registration_audit(event) VALUES(%s::jsonb)",
      (_json(event),))
    return True

def upsert_memory(record):
    if not neon_enabled(): return False
    init_neon()
    mid=str(record.get("memory_id","")).strip()
    if not mid: return False
    _exec("""
      INSERT INTO anviqo_plant_memory(memory_id,tag,equipment,payload)
      VALUES(%s,%s,%s,%s::jsonb)
      ON CONFLICT(memory_id) DO UPDATE
      SET tag=EXCLUDED.tag,
          equipment=EXCLUDED.equipment,
          payload=EXCLUDED.payload,
          updated_at=NOW()
    """,(mid,record.get("tag",""),record.get("equipment",""),_json(record)))
    return True

def get_memory(tag="",equipment=""):
    if not neon_enabled(): return []
    init_neon()
    if tag:
        rows=_exec(
          "SELECT payload FROM anviqo_plant_memory WHERE tag=%s ORDER BY updated_at DESC",
          (str(tag).strip(),), True)
    elif equipment:
        rows=_exec(
          "SELECT payload FROM anviqo_plant_memory WHERE equipment=%s ORDER BY updated_at DESC",
          (str(equipment).strip(),), True)
    else:
        rows=_exec(
          "SELECT payload FROM anviqo_plant_memory ORDER BY updated_at DESC",
          (), True)
    return [r[0] for r in rows]

def upsert_field_report(record):
    """Persist one field report with a stable ID and trusted tenant scope.

    A report must have organization + plant scope before it can enter durable
    storage. In request context, tenant IDs come from the authenticated session,
    never from client-supplied report fields. Existing explicit IDs are retained
    for idempotent retries; generated IDs are deterministic across restarts.
    """
    if not neon_enabled():
        return False
    init_neon()

    record = dict(record or {})
    if not record:
        return False

    try:
        from flask import has_request_context, session
        if has_request_context():
            if not session.get("authenticated") and not session.get("user_id"):
                return False
            org_id = str(session.get("organization_id", "")).strip()
            plant_id = str(session.get("plant_id", "")).strip()
            if not org_id or not plant_id:
                return False
            # Never trust tenant identifiers submitted in a report payload.
            record["organization_id"] = org_id
            record["plant_id"] = plant_id
    except RuntimeError:
        # Flask may be installed without an active request context. The caller
        # must then provide explicit tenant metadata for durable storage.
        pass

    org_id = str(record.get("organization_id", "")).strip()
    plant_id = str(record.get("plant_id", "")).strip()
    if not org_id or not plant_id:
        return False

    rid = str(record.get("report_id", "")).strip()
    if not rid:
        # Python's hash() is process-randomized; use a stable digest instead.
        import hashlib
        identity = _json({
            "organization_id": org_id,
            "plant_id": plant_id,
            "tag": str(record.get("tag", "")).strip().upper(),
            "equipment": str(record.get("equipment", "")).strip(),
            "event": str(record.get("event", "")).strip(),
            "observation": str(record.get("observation", "")).strip(),
            "finding": str(record.get("finding", "")).strip(),
            "maintenance_action": str(record.get("maintenance_action", "")).strip(),
            "outcome": str(record.get("outcome", "")).strip(),
            "raw_report": str(record.get("raw_report", "")).strip(),
        })
        rid = "FR-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    record["report_id"] = rid

    _exec("""
      INSERT INTO anviqo_field_reports(report_id,tag,equipment,payload)
      VALUES(%s,%s,%s,%s::jsonb)
      ON CONFLICT(report_id) DO UPDATE
      SET tag=EXCLUDED.tag,
          equipment=EXCLUDED.equipment,
          payload=EXCLUDED.payload
    """, (rid, record.get("tag", ""), record.get("equipment", ""), _json(record)))
    return True

def upsert_critical_spare(spare_key, tag, payload):
    if not neon_enabled(): return False
    init_neon()
    _exec("""
      INSERT INTO anviqo_critical_spares(spare_key,tag,payload)
      VALUES(%s,%s,%s::jsonb)
      ON CONFLICT(spare_key) DO UPDATE
      SET tag=EXCLUDED.tag,
          payload=EXCLUDED.payload,
          updated_at=NOW()
    """,(str(spare_key),str(tag),_json(payload)))
    return True

def get_critical_spare(tag):
    if not neon_enabled(): return None
    init_neon()
    rows=_exec(
      "SELECT payload FROM anviqo_critical_spares WHERE tag=%s",
      (str(tag).strip(),), True)
    return rows[0][0] if rows else None

def record_spare_transaction(tag,action,quantity,before_qty,after_qty,payload=None):
    if not neon_enabled(): return False
    init_neon()
    _exec("""
      INSERT INTO anviqo_spare_transactions
      (tag,action,quantity,before_qty,after_qty,payload)
      VALUES(%s,%s,%s,%s,%s,%s::jsonb)
    """,(str(tag),str(action),int(quantity),int(before_qty),
         int(after_qty),_json(payload or {})))
    return True
