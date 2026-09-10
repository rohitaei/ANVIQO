"""ANVIQO Universal Industrial Language Layer.

Converts technician/maintenance prose into deterministic industrial facts.
This is an interpretation layer only: it does not write PLC/SCADA, authorize
work, change verification state, or mutate inventory.

The layer intentionally accepts imperfect field language, including:
- FT205 / FT-205 / FT 205
- "found faulty", "checked and found bad"
- "replaced ... with a new FT-205, 1 no spare used"
- "used one FT-205 spare"
- "1 no spare used"
- common quantity words and technician abbreviations.
"""
from __future__ import annotations
import re

_NUM = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
_TAG = r"[A-Z]{1,8}[-_ ]?\d{1,5}"
_QTY = r"one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?"


def normalise_tag(value: str) -> str:
    return str(value or "").strip().upper().replace("_", "-").replace(" ", "-")


def quantity(value: str | None, default: float = 1) -> float:
    if not value:
        return default
    value = str(value).strip().lower()
    return float(_NUM.get(value, value))


def extract_spare_usage(text: str) -> tuple[str, float] | None:
    """Extract only an explicit spare consumption statement.

    Replacement language is handled semantically: the replacement tag closest
    to an explicit quantity + 'spare used' is the spare, not necessarily the
    first equipment tag in the sentence.
    """
    text = str(text or "").strip()
    if not text:
        return None

    patterns = [
        rf"\b(?:used|consumed|removed)\s+(?P<qty>{_QTY})\s+(?P<tag>{_TAG})\s+spares?\b",
        rf"\b(?P<qty>{_QTY})\s+(?P<tag>{_TAG})\s+spares?\s+(?:used|consumed|removed)\b",
        rf"\b(?P<tag>{_TAG})\s+spare\s+(?:used|consumed|removed)\b",
        rf"\breplaced\s+by\s+(?:(?:a|an|the)\s+)?(?:new\s+)?(?P<tag>{_TAG})\s+(?P<qty>{_QTY})\s+nos?\s+spare\s+used\b",
        rf"\breplaced\b.*?\b(?:with|by)\s+(?:(?:a|an|the)\s+)?(?:new\s+)?(?P<tag>{_TAG})\s*,?\s*(?P<qty>{_QTY})\s+nos?\s+(?:(?:of|for)\s+)?(?:(?:the)\s+)?spare\s+used\b",
        rf"\b(?:replacement|replaced)\b.*?\b(?P<tag>{_TAG})\s*,?\s*(?P<qty>{_QTY})\s+nos?\s+(?:(?:of|for)\s+)?(?:(?:the)\s+)?spare\s+used\b",
        rf"\b(?P<tag>{_TAG})\s*,?\s*(?P<qty>{_QTY})\s+nos?\s+spare\s+(?:was\s+)?used\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return normalise_tag(match.group("tag")), quantity(match.groupdict().get("qty"))

    # Explicit "x 1" form.
    match = re.search(rf"\b(?P<tag>{_TAG})\s*x\s*(?P<qty>\d+(?:\.\d+)?)\b", text, re.I)
    if match and re.search(r"\b(?:spare|spares)\b", text, re.I):
        return normalise_tag(match.group("tag")), quantity(match.group("qty"))

    return None


def understand(text: str) -> dict:
    """Return a small, auditable semantic representation of technician prose."""
    text = str(text or "").strip()
    low = text.lower()
    tags = [normalise_tag(m.group(1)) for m in re.finditer(rf"\b({_TAG})\b", text, re.I)]
    spare = extract_spare_usage(text)
    return {
        "asset_tags": list(dict.fromkeys(tags)),
        "spare_used": {"tag": spare[0], "quantity": spare[1]} if spare else None,
        "fault_indicators": [x for x in ("faulty","failed","abnormal","fluctuating","dropping to zero","no indication") if x in low],
        "replacement_detected": bool(re.search(r"\b(?:replaced|replacement|changed|new)\b", low)),
        "recovery_indicators": [x for x in ("now ok","back to normal","stable and normal","working normally","operating normally","returned to normal") if x in low],
        "explicit_spare_consumption": bool(spare),
    }
