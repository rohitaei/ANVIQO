"""Durable idempotency guard for technician field-report spare sync.

This layer belongs to the field-report workflow. It does not change the
Critical Spares V1.6.6 engine or its quantity rules. When Neon is available,
the applied field-report/report-id + tag + quantity record survives Render
restarts; the existing local ledger remains the fallback.
"""
from __future__ import annotations
import re


def _canonical_tag(tag: str) -> str:
    """Use one stable key for equivalent engineering-tag separators."""
    value = str(tag or "").strip().upper()
    return re.sub(r"-+", "-", re.sub(r"[\s_]+", "-", value))



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
        canonical = _canonical_tag(tag)
        rows = _exec("""
          SELECT before_qty, after_qty, transaction_id
          FROM anviqo_field_report_spare_sync
          WHERE report_id=%s AND tag=%s AND quantity=%s AND status='APPLIED'
          LIMIT 1
        """, (str(report_id), canonical, float(quantity)), True)
        # Read legacy ledger keys written before tag canonicalization so a
        # restart cannot accidentally apply the same report twice.
        legacy_keys = list(dict.fromkeys((
            str(tag or "").strip().upper(),
            canonical.replace("-", "_"),
            canonical.replace("-", " "),
        )))
        for legacy in legacy_keys:
            if rows:
                break
            if not legacy or legacy == canonical:
                continue
            rows = _exec("""
              SELECT before_qty, after_qty, transaction_id
              FROM anviqo_field_report_spare_sync
              WHERE report_id=%s AND tag=%s AND quantity=%s AND status='APPLIED'
              LIMIT 1
            """, (str(report_id), legacy, float(quantity)), True)
        if not rows:
            return None
        before, after, transaction_id = rows[0]
        return {
            "status": "ALREADY_APPLIED",
            "inventory_changed": False,
            "tag": canonical,
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
            str(report_id), _canonical_tag(tag), float(quantity),
            float(before), float(after), str(transaction_id or ""),
        ))
        return True
    except Exception:
        return False
