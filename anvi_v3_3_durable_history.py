"""V3.3 durable historical evidence and prediction validation store.

SQLite is the deterministic reference backend for test/PoV use. The contract is
tenant/plant scoped and can be mapped to PostgreSQL/Timescale without changing
the normalized API. No PLC/SCADA write capability exists here.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
import sqlite3
from typing import Optional

from anvi_v2_realtime_store import TelemetryPoint
from anvi_v3_2_historical_evidence import SAFETY


def _utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return ts.astimezone(timezone.utc)


class DurableHistoricalStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.getenv("ANVIQO_V3_HISTORY_DB", "/tmp/anviqo_v3_3_history.db")
        self._init()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init(self):
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS observations (
                observation_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                plant_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                value_json TEXT NOT NULL,
                engineering_unit TEXT NOT NULL,
                quality TEXT NOT NULL,
                source TEXT NOT NULL,
                sequence INTEGER,
                UNIQUE(organization_id, plant_id, tag, timestamp, source, sequence)
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_obs_scope_tag_time
                ON observations(organization_id, plant_id, tag, timestamp)""")
            db.execute("""CREATE TABLE IF NOT EXISTS predictions (
                prediction_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                plant_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL,
                target_time TEXT NOT NULL,
                predicted_value REAL NOT NULL,
                model TEXT NOT NULL,
                evidence_status TEXT NOT NULL,
                actual_value REAL,
                absolute_error REAL,
                validation_status TEXT NOT NULL,
                operator_feedback TEXT
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_pred_scope_tag_time
                ON predictions(organization_id, plant_id, tag, target_time)""")

    def append(self, point: TelemetryPoint) -> bool:
        _utc(point.timestamp)
        with self._connect() as db:
            cur = db.execute(
                """INSERT OR IGNORE INTO observations
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (point.observation_id, point.organization_id, point.plant_id,
                 point.tag, _utc(point.timestamp).isoformat(),
                 json.dumps(point.value, sort_keys=True), point.engineering_unit,
                 point.quality.upper(), point.source,
                 point.sequence),
            )
            return cur.rowcount == 1

    def query(self, organization_id: str, plant_id: str, tag: str,
              start: Optional[datetime] = None, end: Optional[datetime] = None) -> list[TelemetryPoint]:
        args = [organization_id, plant_id, tag]
        clauses = ["organization_id=?", "plant_id=?", "tag=?"]
        if start:
            clauses.append("timestamp>=?")
            args.append(_utc(start).isoformat())
        if end:
            clauses.append("timestamp<=?")
            args.append(_utc(end).isoformat())
        with self._connect() as db:
            rows = db.execute(
                "SELECT timestamp,value_json,engineering_unit,quality,source,sequence "
                "FROM observations WHERE " + " AND ".join(clauses) + " ORDER BY timestamp",
                args,
            ).fetchall()
        return [
            TelemetryPoint(organization_id, plant_id, tag, datetime.fromisoformat(ts),
                           json.loads(value), unit, quality, source, sequence)
            for ts, value, unit, quality, source, sequence in rows
        ]

    def record_prediction(self, *, organization_id: str, plant_id: str, tag: str,
                          target_time: datetime, predicted_value: float, model: str,
                          evidence_status: str, prediction_id: str,
                          created_at: Optional[datetime] = None,
                          operator_feedback: Optional[str] = None) -> dict:
        created = _utc(created_at or datetime.now(timezone.utc))
        target = _utc(target_time)
        if evidence_status != "READY_FOR_VALIDATION":
            raise ValueError("PREDICTION_EVIDENCE_INSUFFICIENT")
        with self._connect() as db:
            db.execute("""INSERT OR IGNORE INTO predictions
                (prediction_id,organization_id,plant_id,tag,created_at,target_time,
                 predicted_value,model,evidence_status,actual_value,absolute_error,
                 validation_status,operator_feedback)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (prediction_id, organization_id, plant_id, tag, created.isoformat(),
                 target.isoformat(), float(predicted_value), model, evidence_status,
                 None, None, "PENDING", operator_feedback))
        return self.get_prediction(prediction_id)

    def get_prediction(self, prediction_id: str) -> dict:
        with self._connect() as db:
            row = db.execute("""SELECT prediction_id,organization_id,plant_id,tag,
                created_at,target_time,predicted_value,model,evidence_status,
                actual_value,absolute_error,validation_status,operator_feedback
                FROM predictions WHERE prediction_id=?""", (prediction_id,)).fetchone()
        if not row:
            raise KeyError("PREDICTION_NOT_FOUND")
        keys = ["prediction_id","organization_id","plant_id","tag","created_at","target_time",
                "predicted_value","model","evidence_status","actual_value","absolute_error",
                "validation_status","operator_feedback"]
        return dict(zip(keys, row))

    def validate_due(self, *, organization_id: str, plant_id: str, tag: str,
                     prediction_id: str, tolerance: float = 0.0) -> dict:
        prediction = self.get_prediction(prediction_id)
        if prediction["organization_id"] != organization_id or prediction["plant_id"] != plant_id or prediction["tag"] != tag:
            raise PermissionError("TENANT_BOUNDARY_VIOLATION")
        target = datetime.fromisoformat(prediction["target_time"])
        rows = self.query(organization_id, plant_id, tag, start=target)
        numeric = [p for p in rows if isinstance(p.value, (int, float)) and not isinstance(p.value, bool)]
        if not numeric:
            prediction["validation_status"] = "PENDING_NO_ACTUAL"
            prediction["safety"] = dict(SAFETY)
            return prediction
        actual = float(numeric[0].value)
        error = abs(actual - float(prediction["predicted_value"]))
        status = "VALIDATED" if error <= max(0.0, tolerance) else "VALIDATED_MISSED"
        with self._connect() as db:
            db.execute("""UPDATE predictions SET actual_value=?,absolute_error=?,
                validation_status=? WHERE prediction_id=?""",
                (actual, error, status, prediction_id))
        prediction = self.get_prediction(prediction_id)
        prediction["safety"] = dict(SAFETY)
        prediction["evidence"] = {"actual_timestamp": numeric[0].timestamp.isoformat()}
        return prediction

    def snapshot(self) -> dict:
        with self._connect() as db:
            observations = db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            predictions = db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        return {"observations": observations, "predictions": predictions,
                "durable": True, "plc_write": False, "scada_control": False,
                "safety": dict(SAFETY)}
