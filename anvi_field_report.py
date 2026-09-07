"""
ANVIQO FIELD REPORT INGESTION V1

Purpose:
- Extract structured maintenance/event information from natural technician reports.
- Accept pasted text and extracted document text.
- Never invent root cause.
- Store conversational reports as PENDING_VERIFICATION.
- Does not perform PLC/SCADA writes.
- Does not create a new reasoning engine.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "automatic_authorization": False,
    "causation_claim": False,
}


TAG_RE = re.compile(
    r"\b([A-Z]{1,8}[-_ ]?\d{1,5})\b",
    re.I,
)


def _clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _first_tag(text):
    for match in TAG_RE.finditer(text):
        tag = match.group(1).upper().replace("_", "-").replace(" ", "-")
        # Avoid interpreting ordinary words followed by numbers as tags.
        if re.match(r"^[A-Z]{1,8}-\d{1,5}$", tag):
            return tag
    return ""


def _extract_present_with(text):
    patterns = [
        r"\bwith\s+(?:a\s+)?(?:present|presence)\s+(?:of\s+)?([A-Za-z][A-Za-z .'-]{2,60})",
        r"\bpresent\s+with\s+([A-Za-z][A-Za-z .'-]{2,60})",
        r"\bwith\s+([A-Z][A-Za-z .'-]{2,40})\s*$",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            value = _clean(m.group(1))
            value = re.sub(r"[.,;]+$", "", value)
            if value:
                return value
    return ""


def _extract_field(text, labels):
    for label in labels:
        m = re.search(
            rf"\b{re.escape(label)}\s*[:=-]\s*(.+?)(?=\n|$)",
            text,
            re.I,
        )
        if m:
            return _clean(m.group(1))
    return ""


def _extract_equipment(text, tag):
    if tag:
        # Known tag is the safest equipment identifier.
        return tag

    patterns = [
        r"\b(?:equipment|instrument|device|unit)\s*[:=-]\s*([A-Za-z0-9 _./-]+)",
        r"\b(UPS[- ]?\d+)\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return _clean(m.group(1))
    return ""


def _extract_location(text):
    patterns = [
        # Natural field-report phrasing:
        r"\bvisit(?:ed)?\s+to\s+(?:the\s+)?([A-Za-z][A-Za-z0-9 /&-]{2,80}?)(?=\s*,|\s+I\s+(?:noticed|saw|then)|\s+noticed|\s+saw|\.|$)",

        # Explicit location phrasing:
        r"\b(?:at|in)\s+(?:the\s+)?(main\s+center\s+plant)\b",
        r"\b(?:at|in)\s+(?:the\s+)?([A-Za-z][A-Za-z0-9 /&-]{2,80}?)(?=\s*,|\s+I\s+(?:noticed|saw|then)|\s+noticed|\s+saw|\.|$)",
        r"\bfrom\s+(?:the\s+)?([A-Za-z][A-Za-z0-9 /&-]{2,80}?)(?=\s*,|\s+I\s+(?:noticed|saw|then)|\s+noticed|\s+saw|\.|$)",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            value = re.sub(r"\s+", " ", m.group(1).strip(" ,.;:"))
            if value:
                return value

    return ""

def _extract_observation(text):
    patterns = [
        r"\bnoticed\s+that\s+(.+?)(?=\.\s+I\s+then|\.\s+After|\.\s+However|$)",
        r"\bobserved\s+that\s+(.+?)(?=\.\s+I\s+then|\.\s+After|\.\s+However|$)",
        r"\bproblem\s*[:=-]\s*(.+?)(?:\n|$)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I | re.S)
        if m:
            return _clean(m.group(1))
    return ""


def _extract_finding(text):
    patterns = [
        r"\bchecked\s+(.+?)(?=\.|\n|$)",
        r"\bfound\s+(.+?)(?=\.|\n|$)",
        r"\bchecking\s+(.+?)(?=\.|\n|$)",
    ]
    values = []
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            value = _clean(m.group(1))
            if value and value not in values:
                values.append(value)
    return "; ".join(values[:5])


def _extract_action(text):
    patterns = [
        r"\bI\s+(?:then\s+)?(.+?)(?=\.?\s+(?:After that|However|But|Then|Finally)\b|$)",
        r"\b(?:action|work done|rectification)\s*[:=-]\s*(.+?)(?:\n|$)",
    ]
    values = []
    for p in patterns:
        for m in re.finditer(p, text, re.I | re.S):
            value = _clean(m.group(1))
            if value and len(value) > 3:
                values.append(value)
    return "; ".join(values[:5])


def _extract_outcome(text):
    patterns = [
        r"\b(?:now|currently)\s+(?:it\s+is\s+)?(.+?)(?:\.|$)",
        r"\b(?:returned|return)\s+to\s+(.+?)(?:\.|$)",
        r"\b(?:everything|system|instrument|unit)\s+(?:is|was)\s+(.+?)(?:\.|$)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return _clean(m.group(1))
    return ""


def _extract_recovery(text):
    low = text.lower()

    if any(x in low for x in [
        "now ok",
        "now normal",
        "returned to normal",
        "back to normal",
        "healthy signal restored",
        "working normally",
        "working normal",
    ]):
        return "Recovered"

    if any(x in low for x in [
        "still abnormal",
        "still faulty",
        "still not working",
        "still fluctuating",
        "intermittent",
        "blinking intermittently",
    ]):
        return "Not fully recovered / requires verification"

    return ""


def _extract_spare(text):
    m = re.search(
        r"\b(?:used|replaced with|replacement)\s+(?:one\s+|a\s+)?"
        r"([A-Z]{1,8}[-_ ]?\d{1,5})",
        text,
        re.I,
    )
    if m:
        return m.group(1).upper().replace("_", "-").replace(" ", "-")
    return ""


def parse_field_report(text, filename=""):
    text = str(text or "").strip()
    if not text:
        raise ValueError("Field report is empty.")

    tag = _first_tag(text)
    equipment = _extract_equipment(text, tag)
    location = _extract_location(text)
    present_with = _extract_present_with(text)
    observation = _extract_observation(text)
    finding = _extract_finding(text)
    action = _extract_action(text)
    outcome = _extract_outcome(text)
    recovery = _extract_recovery(text)
    spare = _extract_spare(text)

    # Deterministic PT example:
    # "PT-303 was not showing anything checked fuse blown no power
    #  changed fuse now ok"
    low = text.lower()

    if not observation and ("not showing" in low or "not showing any" in low):
        observation = "No indication / no visible indication"

    if not finding and ("fuse blown" in low or "fuse" in low and "no power" in low):
        finding = "Fuse blown / no power"

    if not action and ("changed fuse" in low or "replaced fuse" in low):
        action = "Fuse replaced"

    if not outcome and "now ok" in low:
        outcome = "Instrument returned to normal operation"

    if not recovery:
        recovery = _extract_recovery(text)

    # Do not invent a root cause.
    root_cause = ""

    notes = (
        f"Source type: technician field report. "
        f"Source file: {filename or 'pasted report'}. "
        f"Reported at: {datetime.now().isoformat(timespec='seconds')}."
    )

    if present_with:
        notes += f" Present with: {present_with}."

    if not tag and not equipment:
        raise ValueError(
            "Could not identify an equipment tag or equipment name from the report."
        )

    return {
        "event": observation or "Technician field report",
        "equipment": equipment or tag,
        "tag": tag,
        "area": location,
        "observation": observation,
        "finding": finding,
        "maintenance_action": action,
        "confirmation_evidence": outcome,
        "outcome": outcome,
        "recovery_status": recovery,
        "spare_used": spare,
        "source": "technician field report",
        "root_cause": root_cause,
        "notes": notes,
        "raw_report": text,
        "source_file": filename or "",
        "present_with": present_with,
        **SAFETY,
    }


def store_field_report(text, filename=""):
    record = parse_field_report(text, filename)

    import plant_memory

    # Existing Plant Memory remains authoritative.
    # Conversational reports remain pending until human verification.
    memory = plant_memory.create_conversational_memory(
        event=record["event"],
        equipment=record["equipment"],
        tag=record["tag"],
        area=record["area"],
        source=record["source"],
        observation=record["observation"],
        maintenance_action=record["maintenance_action"],
        finding=record["finding"],
        confirmation_evidence=record["confirmation_evidence"],
        outcome=record["outcome"],
        recovery_status=record["recovery_status"],
        spare_used=record["spare_used"],
        notes=(
            record["notes"]
            + f" Raw report: {record['raw_report']}"
            + (f" Present with: {record['present_with']}."
               if record["present_with"] else "")
        ),
    )

    return {
        "status": "PENDING_VERIFICATION",
        "domain": "plant_memory",
        "memory": memory,
        "parsed_report": record,
        **SAFETY,
    }
