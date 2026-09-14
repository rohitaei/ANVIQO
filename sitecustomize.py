"""ANVIQO runtime compatibility hooks.

Loaded automatically by Python's site initialization. This narrowly normalizes
one natural-language field-report pattern that the existing parser previously
missed. It does not alter V5, PCI, PLC/SCADA controls, or spare inventory rules.
"""
from __future__ import annotations
import re

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

# Tenant chat boundary: new plants are fail-closed and cannot fall back to
# global V5/PCI knowledge. Primary Plant retains the proven V5 compatibility path.
try:
    import anvi_tenant_chat_boundary
except Exception:
    pass

# V14 importer: the durable job table is created by the authenticated enqueue
# path before a job exists. Avoid repeating PostgreSQL DDL/index creation from
# every worker polling cycle; that DDL can block the worker behind catalog locks.
try:
    import anvi_plant_data_import as _anvi_import
    if not getattr(_anvi_import, "_ANVIQO_SCHEMA_LOOP_BYPASS", False):
        _anvi_import._ANVIQO_SCHEMA_LOOP_BYPASS = True
        _anvi_import._job_schema = lambda: None

    # Some engineering workbooks contain large formatted regions with no data.
    # Bound consecutive empty rows so universal onboarding cannot spend minutes
    # walking formatting-only rows while still retaining normal sparse sheets.
    if not getattr(_anvi_import, "_ANVIQO_SPARSE_XLSX_BOUND", False):
        _anvi_import._ANVIQO_SPARSE_XLSX_BOUND = True
        def _bounded_xlsx_records(raw):
            from openpyxl import load_workbook
            wb = load_workbook(__import__('io').BytesIO(bytes(raw)), read_only=True, data_only=True)
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
                                if empty >= 5000:
                                    break
                    yield from _anvi_import._matrix_records(ws.title, rows_with_bound())
            finally:
                wb.close()
        _anvi_import._xlsx_records = _bounded_xlsx_records
except Exception:
    pass
