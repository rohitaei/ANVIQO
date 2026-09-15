"""ANVIQO runtime compatibility hooks.

Loaded automatically by Python's site initialization. This narrowly normalizes
one natural-language field-report pattern that the existing parser previously
missed. It does not alter V5, PCI, PLC/SCADA controls, or spare inventory rules.
"""
from __future__ import annotations
import re
from contextlib import contextmanager
import threading

def _install_field_report_spare_compat():
    try:
        import anvi_field_report
    except Exception:
        return
    original = getattr(anvi_field_report, "parse_field_report", None)
    if not callable(original) or getattr(original, "_anviqo_spare_compat", False):
        return
    pattern = re.compile(r"\breplaced\s+by\s+(?:a|an|new\s+)?(?P<tag>[A-Z]{1,8}[-_ ]?\d{1,5})\s+(?P<qty>one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)\s+nos?\s+spare\s+used\b", re.I)
    number_words = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
    def patched_parse_field_report(text, filename=""):
        report = original(text, filename)
        match = pattern.search(str(text or ""))
        if match:
            tag = match.group("tag").upper().replace("_", "-").replace(" ", "-")
            qty_raw = match.group("qty")
            qty = number_words.get(qty_raw.lower(), qty_raw)
            report["spare_used"] = f"{tag} x{qty}"
        return report
    patched_parse_field_report._anviqo_spare_compat = True
    anvi_field_report.parse_field_report = patched_parse_field_report

_install_field_report_spare_compat()

try:
    import anvi_tenant_chat_boundary
except Exception:
    pass

# V14 importer runtime safeguards. The authenticated enqueue path creates the
# durable job table before work exists; worker polling must not repeatedly run
# PostgreSQL DDL/index creation. Excel parsing is bounded for formatting-only
# regions, and database writes are isolated per record so one blocked/conflicting
# row cannot wedge the whole universal onboarding job.
try:
    import anvi_plant_data_import as _anvi_import
    import anvi_tenant_store as _anvi_store
    if not getattr(_anvi_import, "_ANVIQO_SCHEMA_LOOP_BYPASS", False):
        _anvi_import._ANVIQO_SCHEMA_LOOP_BYPASS = True
        _anvi_import._job_schema = lambda: None

    if not getattr(_anvi_import, "_ANVIQO_SPARSE_XLSX_BOUND", False):
        _anvi_import._ANVIQO_SPARSE_XLSX_BOUND = True
        def _bounded_xlsx_records(raw):
            from openpyxl import load_workbook
            import io
            wb = load_workbook(io.BytesIO(bytes(raw)), read_only=True, data_only=True, keep_links=False)
            try:
                for ws in wb.worksheets:
                    def rows_with_bound():
                        empty = 0
                        for row in ws.iter_rows(values_only=True):
                            if any(v is not None and str(v).strip() for v in row):
                                empty = 0
                                yield row
                            else:
                                empty += 1
                                if empty >= 1000:
                                    break
                    yield from _anvi_import._matrix_records(ws.title, rows_with_bound())
            finally:
                wb.close()
        _anvi_import._xlsx_records = _bounded_xlsx_records

    if not getattr(_anvi_import, "_ANVIQO_BATCH_RESILIENT", False):
        _anvi_import._ANVIQO_BATCH_RESILIENT = True
        _importing = threading.local()
        _original_connect = _anvi_store._connect
        @contextmanager
        def _connect_with_import_timeout():
            with _original_connect() as conn:
                if getattr(_importing, "active", False) and not _anvi_store._is_sqlite():
                    conn.execute("SET LOCAL lock_timeout = '3000'")
                    conn.execute("SET LOCAL statement_timeout = '5000'")
                yield conn
        _anvi_store._connect = _connect_with_import_timeout
        _original_insert_batch = _anvi_import._insert_batch
        def _resilient_insert_batch(plant_id, org_id, document_id, digest, records):
            # Deliberately use a fresh DB transaction for each record. The old
            # batch-level executemany could remain blocked even though timeout
            # guards were installed, preventing the durable worker from making
            # progress. Per-record isolation keeps the universal import moving
            # and records an individual bad row instead of wedging the job.
            _importing.active = True
            inserted = 0
            errors = []
            try:
                for record in records:
                    try:
                        a, e = _original_insert_batch(plant_id, org_id, document_id, digest, [record])
                        inserted += a
                        errors.extend(e)
                    except Exception as exc:
                        print(f"ANVIQO_IMPORT_BAD_RECORD document={document_id} error={exc!r}", flush=True)
                        errors.append(str(exc))
                return inserted, errors
            finally:
                _importing.active = False
        _anvi_import._insert_batch = _resilient_insert_batch

    if not getattr(_anvi_import, "_ANVIQO_BATCH_TRACE", False):
        _anvi_import._ANVIQO_BATCH_TRACE = True
        _previous_insert = _anvi_import._insert_batch
        def _traced_insert_batch(plant_id, org_id, document_id, digest, records):
            print(f"ANVIQO_IMPORT_BATCH start size={len(records)} document={document_id}", flush=True)
            result = _previous_insert(plant_id, org_id, document_id, digest, records)
            print(f"ANVIQO_IMPORT_BATCH done size={len(records)} inserted={result[0]} errors={len(result[1])}", flush=True)
            return result
        _anvi_import._insert_batch = _traced_insert_batch
except Exception:
    pass
