"""Durable idempotency guard for technician field-report spare sync.

This layer belongs to the field-report workflow. It does not change the
Critical Spares V1.6.6 engine or its quantity rules. When Neon is available,
the applied field-report/report-id + tag + quantity record survives Render
restarts; the existing local ledger remains the fallback.
"""
from __future__ import annotations


def _neon_ready() -> bool:
    try:
        from anvi_neon_store import neon_enabled, _exec
        if not neon_enabled():
            return False
        _exec("""
          CREATE TABLE IF NOT EXISTS anviqo_field_report_spare_sync(
            report_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            quantity DOUBLE PRECISION NOT NULL,
            before_qty DOUBLE PRECISION,
            after_qty DOUBLE PRECISION,
            transaction_id TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY(report_id, tag, quantity)
          )
        """)
        return True
    except Exception:
        return False


def get_applied(report_id: str, tag: str, quantity: float):
    """Return a durable applied record, or None when not recorded."""
    if not _neon_ready():
        return None
    try:
        from anvi_neon_store import _exec
        rows = _exec("""
          SELECT before_qty, after_qty, transaction_id
          FROM anviqo_field_report_spare_sync
          WHERE report_id=%s AND tag=%s AND quantity=%s AND status='APPLIED'
          LIMIT 1
        """, (str(report_id), str(tag).upper(), float(quantity)), True)
        if not rows:
            return None
        before, after, transaction_id = rows[0]
        return {
            "status": "ALREADY_APPLIED",
            "inventory_changed": False,
            "tag": str(tag).upper(),
            "quantity": float(quantity),
            "before": before,
            "after": after,
            "transaction_id": transaction_id,
            "report_id": str(report_id),
        }
    except Exception:
        return None


def record_applied(report_id: str, tag: str, quantity: float, before, after, transaction_id: str):
    """Persist a successful field-report inventory application."""
    if not _neon_ready():
        return False
    try:
        from anvi_neon_store import _exec
        _exec("""
          INSERT INTO anviqo_field_report_spare_sync
            (report_id, tag, quantity, before_qty, after_qty, transaction_id, status)
          VALUES (%s,%s,%s,%s,%s,%s,'APPLIED')
          ON CONFLICT(report_id, tag, quantity) DO NOTHING
        """, (
            str(report_id), str(tag).upper(), float(quantity),
            float(before), float(after), str(transaction_id or ""),
        ))
        return True
    except Exception:
        return False
