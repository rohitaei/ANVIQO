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

    pattern = re.compile(
        r"\breplaced\s+by\s+(?:a|an|new\s+)?"
        r"(?P<tag>[A-Z]{1,8}[-_ ]?\d{1,5})\s+"
        r"(?P<qty>one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)\s+"
        r"nos?\s+spare\s+used\b",
        re.I,
    )
    number_words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }

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
