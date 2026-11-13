"""Deterministic intent detection for family-level spare inventory questions."""
from __future__ import annotations
import re

_STOCK_INTENT = re.compile(
    r"\b(?:spare|spares|stock|inventory|zero\s+stock|out\s+of\s+stock|shortage|available)\b",
    re.IGNORECASE,
)
_EXACT_TAG = re.compile(
    r"\b(?:PT|FT|LT|RTD|TE|SOV|FSV|PCV|MCV|AT|WT|AI|AO|DI|DO)[-_ ]?\d{1,6}[A-Z]?\b",
    re.IGNORECASE,
)
_FAMILIES = (
    ("PT", re.compile(r"\b(?:PT|pressure(?:\s+(?:transmitter|instrument|sensor))?)\b", re.I)),
    ("FT", re.compile(r"\b(?:FT|flow(?:\s+(?:transmitter|meter|sensor))?)\b", re.I)),
    ("LT", re.compile(r"\b(?:LT|level(?:\s+(?:transmitter|sensor))?)\b", re.I)),
    ("RTD", re.compile(r"\b(?:RTD|TE|thermocouple|temperature\s+(?:element|sensor|transmitter))\b", re.I)),
    ("SOV", re.compile(r"\b(?:SOV|solenoid(?:\s+valve)?)\b", re.I)),
    ("FSV&PCV", re.compile(r"\b(?:FSV|PCV|shut\s*off\s+valve|pneumatic\s+valve)\b", re.I)),
    ("MCV", re.compile(r"\b(?:MCV|motorized\s+(?:control\s+)?valve)\b", re.I)),
    ("LOAD CELL", re.compile(r"\b(?:load\s*cell|loadcell)\b", re.I)),
    ("Analyser", re.compile(r"\b(?:analyser|analyzer)\b", re.I)),
    ("AIR COMPRESSOR", re.compile(r"\bair\s+compressor\b", re.I)),
)


def classify_spare_family_query(question: str) -> str | None:
    """Return an inventory family only for family-level stock questions."""
    q = str(question or "").strip()
    if not q or not _STOCK_INTENT.search(q) or _EXACT_TAG.search(q):
        return None
    for family, pattern in _FAMILIES:
        if pattern.search(q):
            return family
    return None
