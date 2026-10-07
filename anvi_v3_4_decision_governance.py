"""V3.4 human-governed decision trace.

Records the evidence-backed recommendation, the human decision, and the
observed outcome without ever authorizing or executing an OT action.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
import sqlite3
import uuid

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
    "causation_claim": False,
}

DECISIONS = {"PENDING", "APPROVED", "REJECTED", "DEFERRED", "COMPLETED"}
OUTCOMES = {"UNKNOWN", "IMPROVED", "UNCHANGED", "WORSENED", "NOT_OBSERVED"}


def _utc(ts: datetime) -> str:
    if ts.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return ts.astimezone(timezone.utc).isoformat()


class DecisionGovernanceStore:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.getenv("ANVIQO_V3_4_DECISION_DB", "/tmp/anviqo_v3_4_decisions.db")
        self._init()

    def _connect(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        return c

    def _init(self):
        with self._connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                plant_id TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                evidence_ids_json TEXT NOT NULL,
                evidence_status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                decided_at TEXT,
                decision TEXT NOT NULL,
                operator_id TEXT,
                rationale TEXT,
                outcome TEXT NOT NULL,
                outcome_note TEXT,
                outcome_at TEXT
            )""")
            c.execute("""CREATE INDEX IF NOT EXISTS idx_decision_scope
                         ON decisions(organization_id, plant_id, created_at)""")

    def create(self, *, organization_id, plant_id, subject_type, subject_id,
               recommendation, evidence_ids, evidence_status,
               operator_id=None, rationale=None, decision_id=None):
        if not organization_id or not plant_id:
            raise ValueError("organization_id and plant_id are required")
        if evidence_status != "EVIDENCE_AVAILABLE":
            raise ValueError("DECISION_EVIDENCE_INSUFFICIENT")
        if not recommendation.strip():
            raise ValueError("recommendation is required")
        did = decision_id or str(uuid.uuid4())
        with self._connect() as c:
            c.execute("""INSERT INTO decisions
                (decision_id, organization_id, plant_id, subject_type, subject_id,
                 recommendation, evidence_ids_json, evidence_status, created_at,
                 decision, operator_id, rationale, outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, 'UNKNOWN')""",
                (did, organization_id, plant_id, subject_type, subject_id,
                 recommendation, __import__("json").dumps(list(evidence_ids)),
                 evidence_status, _utc(datetime.now(timezone.utc)),
                 operator_id, rationale))
        return self.get(did)

    def decide(self, *, organization_id, plant_id, decision_id, decision,
               operator_id, rationale=None):
        if decision not in DECISIONS - {"PENDING"}:
            raise ValueError("INVALID_HUMAN_DECISION")
        with self._connect() as c:
            row = c.execute("SELECT * FROM decisions WHERE decision_id=? AND organization_id=? AND plant_id=?",
                            (decision_id, organization_id, plant_id)).fetchone()
            if not row:
                raise KeyError("DECISION_NOT_FOUND")
            c.execute("""UPDATE decisions SET decision=?, decided_at=?, operator_id=?,
                         rationale=COALESCE(?, rationale) WHERE decision_id=?""",
                      (decision, _utc(datetime.now(timezone.utc)), operator_id,
                       rationale, decision_id))
        return self.get(decision_id)

    def record_outcome(self, *, organization_id, plant_id, decision_id,
                       outcome, note=None):
        if outcome not in OUTCOMES - {"UNKNOWN"}:
            raise ValueError("INVALID_OUTCOME")
        with self._connect() as c:
            row = c.execute("SELECT * FROM decisions WHERE decision_id=? AND organization_id=? AND plant_id=?",
                            (decision_id, organization_id, plant_id)).fetchone()
            if not row:
                raise KeyError("DECISION_NOT_FOUND")
            if row["decision"] not in {"APPROVED", "COMPLETED"}:
                raise ValueError("HUMAN_DECISION_REQUIRED_BEFORE_OUTCOME")
            c.execute("""UPDATE decisions SET outcome=?, outcome_note=?, outcome_at=?
                         WHERE decision_id=?""",
                      (outcome, note, _utc(datetime.now(timezone.utc)), decision_id))
        return self.get(decision_id)

    def get(self, decision_id):
        with self._connect() as c:
            row = c.execute("SELECT * FROM decisions WHERE decision_id=?", (decision_id,)).fetchone()
        if not row:
            raise KeyError("DECISION_NOT_FOUND")
        d = dict(row)
        d["evidence_ids"] = __import__("json").loads(d.pop("evidence_ids_json"))
        d["safety"] = dict(SAFETY)
        return d

    def list(self, organization_id, plant_id, limit=100):
        with self._connect() as c:
            rows = c.execute("""SELECT decision_id FROM decisions
                                WHERE organization_id=? AND plant_id=?
                                ORDER BY created_at DESC LIMIT ?""",
                             (organization_id, plant_id, max(1, min(int(limit), 1000)))).fetchall()
        return [self.get(r["decision_id"]) for r in rows]

    def snapshot(self, organization_id, plant_id):
        rows = self.list(organization_id, plant_id, 1000)
        return {
            "status": "OK",
            "tenant": {"organization_id": organization_id, "plant_id": plant_id},
            "decision_count": len(rows),
            "pending_count": sum(r["decision"] == "PENDING" for r in rows),
            "approved_count": sum(r["decision"] == "APPROVED" for r in rows),
            "completed_count": sum(r["decision"] == "COMPLETED" for r in rows),
            "outcomes_recorded": sum(r["outcome"] != "UNKNOWN" for r in rows),
            "automatic_execution": False,
            "human_decision_required": True,
            "safety": dict(SAFETY),
        }
