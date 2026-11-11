"""Tenant-bound, read-only PLC telemetry ingress. Cloud never opens PLC sockets."""
from __future__ import annotations
import hmac, json, math, os, re
from datetime import datetime, timezone, timedelta
from flask import jsonify, request, session

_TAG = re.compile(r"^[A-Za-z0-9_.:/-]{1,128}$")
_ALLOWED_QUALITY = {"GOOD", "UNCERTAIN", "BAD"}

def _db_url():
    return os.getenv("ANVIQO_TENANT_DB_URL", "").strip() or os.getenv("DATABASE_URL", "").strip()

def _connect():
    url = _db_url()
    if not url: raise RuntimeError("Tenant PostgreSQL is not configured")
    if url.startswith("sqlite:"):
        import sqlite3
        path = url[7:]
        if path in (":memory:", "//:memory:"): path = ":memory:"
        elif path.startswith("///"): path = path[2:]
        elif path.startswith("//"): path = path[2:]
        conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row
        return conn, True
    import psycopg
    if "sslmode=" not in url.lower(): url += ("&" if "?" in url else "?") + "sslmode=require"
    return psycopg.connect(url), False

def _schema(conn, sqlite):
    cur = conn.cursor()
    sql = """CREATE TABLE IF NOT EXISTS anviqo_plc_telemetry (
      organization_id TEXT NOT NULL, plant_id TEXT NOT NULL, tag TEXT NOT NULL,
      value_json VALUE_TYPE NOT NULL, unit TEXT NOT NULL DEFAULT '', quality TEXT NOT NULL,
      source_timestamp TIME_TYPE NOT NULL, received_at TIME_TYPE NOT NULL, gateway_id TEXT NOT NULL,
      PRIMARY KEY (organization_id, plant_id, tag))"""
    sql = sql.replace("VALUE_TYPE", "TEXT" if sqlite else "JSONB").replace("TIME_TYPE", "TEXT" if sqlite else "TIMESTAMPTZ")
    cur.execute(sql); conn.commit()

def _timestamp(raw):
    if not isinstance(raw, str): raise ValueError("timestamp must be ISO-8601 text")
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None: raise ValueError("timestamp must include timezone")
    dt = dt.astimezone(timezone.utc); now = datetime.now(timezone.utc)
    if dt < now - timedelta(hours=24) or dt > now + timedelta(minutes=5):
        raise ValueError("timestamp outside accepted clock window")
    return dt

def register(app):
    @app.post("/api/gateway/v1/telemetry")
    def plc_gateway_ingest():
        org = os.getenv("ANVIQO_PLC_INGEST_ORG_ID", "").strip()
        plant = os.getenv("ANVIQO_PLC_INGEST_PLANT_ID", "").strip()
        secret = os.getenv("ANVIQO_PLC_INGEST_TOKEN", "").strip()
        if not (org and plant and secret):
            return jsonify(status="DISABLED", reason="PLC_INGEST_NOT_CONFIGURED", read_only=True, plc_write=False, scada_control=False), 503
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:], secret):
            return jsonify(status="UNAUTHORIZED"), 401
        body = request.get_json(silent=True)
        if not isinstance(body, dict): return jsonify(status="INVALID", reason="JSON_OBJECT_REQUIRED"), 400
        gateway = str(body.get("gateway_id") or "").strip()
        points = body.get("points")
        if not gateway or len(gateway) > 80 or not isinstance(points, list) or not 1 <= len(points) <= 2000:
            return jsonify(status="INVALID", reason="GATEWAY_AND_1_TO_2000_POINTS_REQUIRED"), 400
        clean = []
        try:
            for item in points:
                if not isinstance(item, dict): raise ValueError("point must be object")
                tag = str(item.get("tag") or "").strip()
                if not _TAG.fullmatch(tag): raise ValueError("invalid tag")
                value = item.get("value")
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    raise ValueError("value must be finite numeric measurement")
                quality = str(item.get("quality") or "BAD").upper()
                if quality not in _ALLOWED_QUALITY: raise ValueError("invalid quality")
                ts = _timestamp(item.get("timestamp"))
                clean.append((tag, json.dumps(value), str(item.get("unit") or "")[:32], quality, ts, gateway))
        except (ValueError, TypeError) as exc:
            return jsonify(status="INVALID", reason=str(exc)), 400
        conn = None
        try:
            conn, sqlite = _connect(); _schema(conn, sqlite); p = "?" if sqlite else "%s"
            cur = conn.cursor()
            cur.execute(f"SELECT 1 FROM anviqo_plants WHERE organization_id={p} AND plant_id={p} AND status='ACTIVE'", (org, plant))
            if not cur.fetchone():
                conn.rollback()
                return jsonify(status="REJECTED", reason="CONFIGURED_TENANT_PLANT_NOT_FOUND"), 409
            now = datetime.now(timezone.utc).isoformat()
            for tag, value, unit, quality, ts, gw in clean:
                if sqlite:
                    cur.execute(f"""INSERT INTO anviqo_plc_telemetry
                    (organization_id,plant_id,tag,value_json,unit,quality,source_timestamp,received_at,gateway_id)
                    VALUES({p},{p},{p},{p},{p},{p},{p},{p},{p})
                    ON CONFLICT(organization_id,plant_id,tag) DO UPDATE SET value_json=excluded.value_json,
                    unit=excluded.unit,quality=excluded.quality,source_timestamp=excluded.source_timestamp,
                    received_at=excluded.received_at,gateway_id=excluded.gateway_id
                    WHERE excluded.source_timestamp >= anviqo_plc_telemetry.source_timestamp""",
                    (org,plant,tag,value,unit,quality,ts.isoformat(),now,gw))
                else:
                    cur.execute(f"""INSERT INTO anviqo_plc_telemetry
                    (organization_id,plant_id,tag,value_json,unit,quality,source_timestamp,received_at,gateway_id)
                    VALUES({p},{p},{p},{p}::jsonb,{p},{p},{p},{p},{p})
                    ON CONFLICT(organization_id,plant_id,tag) DO UPDATE SET value_json=EXCLUDED.value_json,
                    unit=EXCLUDED.unit,quality=EXCLUDED.quality,source_timestamp=EXCLUDED.source_timestamp,
                    received_at=EXCLUDED.received_at,gateway_id=EXCLUDED.gateway_id
                    WHERE EXCLUDED.source_timestamp >= anviqo_plc_telemetry.source_timestamp""",
                    (org,plant,tag,value,unit,quality,ts,now,gw))
            conn.commit()
            return jsonify(status="ACCEPTED",accepted=len(clean),plant_id=plant,gateway_id=gateway,
                received_at=now,read_only=True,plc_write=False,scada_control=False,human_decision_required=True),202
        except Exception as exc:
            if conn: conn.rollback()
            app.logger.exception("PLC gateway ingestion failed")
            return jsonify(status="ERROR",reason=type(exc).__name__),503
        finally:
            if conn: conn.close()

    @app.get("/api/plc/live")
    def plc_live_snapshot():
        if not session.get("authenticated"): return jsonify(status="UNAUTHORIZED"),401
        org = str(session.get("organization_id") or ""); plant = str(session.get("plant_id") or "")
        if not org or not plant: return jsonify(status="NO_TENANT_CONTEXT",points=[]),409
        conn = None
        try:
            conn, sqlite = _connect(); _schema(conn,sqlite); p = "?" if sqlite else "%s"
            cur = conn.cursor()
            cur.execute(f"""SELECT tag,value_json,unit,quality,source_timestamp,received_at,gateway_id
            FROM anviqo_plc_telemetry WHERE organization_id={p} AND plant_id={p} ORDER BY tag""",(org,plant))
            points=[]; now=datetime.now(timezone.utc)
            for row in cur.fetchall():
                ts = row[4] if isinstance(row[4],datetime) else datetime.fromisoformat(str(row[4]).replace("Z","+00:00"))
                rx = row[5] if isinstance(row[5],datetime) else datetime.fromisoformat(str(row[5]).replace("Z","+00:00"))
                age=max(0,int((now-rx).total_seconds()))
                points.append({"tag":row[0],"value":json.loads(row[1]) if isinstance(row[1],str) else row[1],
                    "unit":row[2],"quality":row[3],"source_timestamp":ts.isoformat(),"received_at":rx.isoformat(),
                    "age_seconds":age,"fresh":age<=10 and row[3]=="GOOD","gateway_id":row[6]})
            status="LIVE" if any(x["fresh"] for x in points) else ("STALE" if points else "NO DATA")
            return jsonify(status=status,mode="LIVE_PLC" if status=="LIVE" else status,
                source="CUSTOMER_OT_READ_ONLY_GATEWAY",points=points,point_count=len(points),
                read_only=True,plc_write=False,scada_control=False,human_decision_required=True)
        except Exception as exc:
            app.logger.exception("PLC live snapshot failed")
            return jsonify(status="ERROR",reason=type(exc).__name__,points=[],read_only=True,plc_write=False,scada_control=False),503
        finally:
            if conn: conn.close()
