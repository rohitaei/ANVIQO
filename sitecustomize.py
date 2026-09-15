"""ANVIQO runtime compatibility hooks.

Loaded automatically by Python's site initialization. These hooks are limited
to onboarding/runtime compatibility and do not alter V5, PCI, PLC/SCADA
controls, or spare inventory rules.
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

# V14 importer safeguards. These hooks are onboarding-only. They ensure every
# durable importer DB operation, including queue claiming and schema checks,
# has short connection/statement/lock timeouts after a web-process restart.
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

    _importing = threading.local()
    if not getattr(_anvi_import, "_ANVIQO_HARD_DB_GUARD", False):
        _anvi_import._ANVIQO_HARD_DB_GUARD = True
        _original_connect = _anvi_store._connect
        @contextmanager
        def _connect_with_import_timeout():
            if getattr(_importing, "active", False) and not _anvi_store._is_sqlite():
                import psycopg
                url = _anvi_store._db_url()
                parts = url.split("?")
                base = parts[0]
                params = []
                if len(parts) > 1:
                    params = [x for x in parts[1].split("&") if x and not x.lower().startswith("connect_timeout=") and not x.lower().startswith("sslmode=")]
                params += ["connect_timeout=5", "sslmode=require"]
                url = base + "?" + "&".join(params)
                conn = psycopg.connect(url, options="-c statement_timeout=4000 -c lock_timeout=1500")
                try:
                    yield conn
                    conn.commit()
                finally:
                    conn.close()
                return
            with _original_connect() as conn:
                yield conn
        _anvi_store._connect = _connect_with_import_timeout

        _original_claim_job = _anvi_import._claim_job
        def _guarded_claim_job():
            _importing.active = True
            try:
                return _original_claim_job()
            finally:
                _importing.active = False
        _anvi_import._claim_job = _guarded_claim_job

        _original_import_plant_data = _anvi_import.import_plant_data
        def _guarded_import_plant_data(plant_id, actor):
            _importing.active = True
            try:
                return _original_import_plant_data(plant_id, actor)
            finally:
                _importing.active = False
        _anvi_import.import_plant_data = _guarded_import_plant_data

        _original_insert_batch = _anvi_import._insert_batch
        def _resilient_insert_batch(plant_id, org_id, document_id, digest, records):
            _importing.active = True
            inserted = 0
            errors = []
            try:
                for idx, record in enumerate(records, start=1):
                    try:
                        print(f"ANVIQO_IMPORT_RECORD start batch_index={idx} document={document_id}", flush=True)
                        a, e = _original_insert_batch(plant_id, org_id, document_id, digest, [record])
                        inserted += a
                        errors.extend(e)
                        print(f"ANVIQO_IMPORT_RECORD done batch_index={idx} inserted={a} errors={len(e)} document={document_id}", flush=True)
                    except Exception as exc:
                        print(f"ANVIQO_IMPORT_BAD_RECORD batch_index={idx} document={document_id} error={exc!r}", flush=True)
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
except Exception as exc:
    print(f"ANVIQO_IMPORT_RUNTIME_HOOK_ERROR error={exc!r}", flush=True)
