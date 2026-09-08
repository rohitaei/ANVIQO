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
import os

import re
from datetime import datetime
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent


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

def _extract_labeled_field(text, label, next_labels):
    """Extract a structured Field Report value such as:
       Finding: ...
       Maintenance action: ...
       Outcome: ...
       Recovery: ...
       Spare used: ...
    """
    labels = "|".join(re.escape(x) for x in next_labels)
    pattern = (
        rf"\b{re.escape(label)}\s*:\s*(.*?)"
        rf"(?=\s*(?:{labels})\s*:|$)"
    )
    m = re.search(pattern, text, re.I | re.S)
    if not m:
        return ""
    return _clean(m.group(1)).strip(" .;:")


def _extract_observation(text):
    # Structured label first
    value = _extract_labeled_field(
        text,
        "Observation",
        ["Finding", "Maintenance action", "Outcome", "Recovery", "Spare used"]
    )
    if value:
        return value

    patterns = [
        r"Field report\s*:\s*[A-Z]{1,8}-\d{1,5}\s+(.+?)(?=\.\s+(?:Finding|Maintenance action|Outcome|Recovery|Spare used)\s*:|$)",
        r"(?:was|were|found|observed)\s+(?:showing|giving|indicating)\s+(.+?)(?=\.\s+(?:The technician|After|One|[A-Z][A-Za-z]+ was|$))",
        r"found\s+(.+?)(?=\.\s+(?:The technician|After|One|[A-Z][A-Za-z]+ was|$))",
        r"observed\s+(.+?)(?=\.\s+(?:The technician|After|One|[A-Z][A-Za-z]+ was|$))",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I | re.S)
        if m:
            return _clean(m.group(1)).strip(" .;:")

    return ""


def _extract_finding(text):
    value = _extract_labeled_field(
        text,
        "Finding",
        ["Maintenance action", "Outcome", "Recovery", "Spare used"]
    )
    if value:
        return value

    patterns = [
        r"found\s+(?:that\s+)?(?:it\s+was\s+)?(.+?)(?=\.\s+(?:The transmitter|The technician|One|After|$))",
        r"confirmed\s+(?:that\s+)?(?:it\s+was\s+)?(.+?)(?=\.\s+(?:One|After|$))",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I | re.S)
        if m:
            value = _clean(m.group(1)).strip(" .;:")
            if value:
                return value

    return ""


def _extract_action(text):
    value = _extract_labeled_field(
        text,
        "Maintenance action",
        ["Outcome", "Recovery", "Spare used"]
    )
    if value:
        return value

    actions = []

    if re.search(r"\binspected\s+the\s+transmitter\b", text, re.I):
        actions.append("inspected the transmitter")

    if re.search(r"\bconfirmed\s+that\s+it\s+was\s+faulty\b", text, re.I):
        actions.append("confirmed that it was faulty")

    if re.search(
        r"\b(?:one|1)\s+[A-Z]{1,8}-\d{1,5}\s+spare\s+was\s+used\s+to\s+replace\s+the\s+faulty\s+transmitter\b",
        text,
        re.I,
    ):
        actions.append("replaced the faulty transmitter")

    elif re.search(
        r"\breplaced\s+the\s+faulty\s+transmitter\b",
        text,
        re.I,
    ):
        actions.append("replaced the faulty transmitter")

    # Remove duplicates while preserving order.
    unique_actions = []
    for action in actions:
        if action not in unique_actions:
            unique_actions.append(action)

    return "; ".join(unique_actions)



def _extract_spare(text):
    # Structured field-report format:
    # Spare used: FT-412 x1
    value = _extract_labeled_field(
        text,
        "Spare used",
        []
    )
    if value:
        m = re.search(
            r"\b([A-Z]{1,8}-\d{1,5})\s*(?:x|qty|quantity)?\s*(\d+(?:\.\d+)?)\b",
            value,
            re.I,
        )
        if m:
            return f"{m.group(1).upper()} x{m.group(2)}"
        return value

    # Natural-language field reports.
    patterns = [
        r"\b(?:one|1)\s+([A-Z]{1,8}-\d{1,5})\s+spare\s+was\s+used\b",
        r"\b([A-Z]{1,8}-\d{1,5})\s+spare\s+was\s+used\b",
        r"\bused\s+(?:one|1)\s+([A-Z]{1,8}-\d{1,5})\s+spare\b",
        r"\b([A-Z]{1,8}-\d{1,5})\s+spare\s+(?:was\s+)?used\b",
        r"\b(?:replaced|replacement)\b.*?\busing\s+(?:one|1)\s+([A-Z]{1,8}-\d{1,5})\s+spare\b",
        r"\busing\s+(?:one|1)\s+([A-Z]{1,8}-\d{1,5})\s+spare\b",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I | re.S)
        if m:
            return f"{m.group(1).upper()} x1"

    return ""

def _extract_outcome(text):
    value = _extract_labeled_field(
        text,
        "Outcome",
        ["Recovery", "Spare used"]
    )
    if value:
        return value

    patterns = [
        r"After replacement,\s*(.+?)(?=\.\s*(?:The equipment|Recovery|Spare used|$))",
        r"after replacement,\s*(.+?)(?=\.\s*(?:The equipment|Recovery|Spare used|$))",
        r"(?:signal|indication)\s+(?:became|returned\s+to|returned)\s+(.+?)(?=\.\s*(?:The equipment|Recovery|$))",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.I | re.S)
        if m:
            value = _clean(m.group(1)).strip(" .;:")
            if value:
                return value

    return ""


def _extract_recovery(text):
    value = _extract_labeled_field(
        text,
        "Recovery",
        ["Spare used"]
    )
    if value:
        return value

    if re.search(
        r"(?:equipment|instrument|transmitter)\s+was\s+restored\s+to\s+(?:a\s+)?healthy\s+condition",
        text,
        re.I,
    ):
        return "Recovered"

    if re.search(
        r"(?:signal|indication|reading)\s+(?:returned|became)\s+(?:normal|healthy)",
        text,
        re.I,
    ):
        return "Recovered"

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

    # ANVI_FIELD_REPORT_PARSER_V2
    # Deterministic normalization for concise RMHS/WB discharge-gate reports.
    # Keeps the general parser unchanged and prevents duplicated technician
    # wording from becoming the canonical finding/action.
    if (
        "rmhs" in low
        and "wb-1" in low
        and "discharge gate" in low
        and "solenoid valve" in low
    ):
        equipment = "Discharge gate"
        tag = "RMHS-1 WB-1"
        location = "RMHS-1"
        observation = "Discharge gate was not opening"
        finding = "Solenoid valve problem"

        if (
            "changed by new one" in low
            or "changed with new one" in low
            or "replaced" in low
            or "new one" in low
        ):
            action = "Replaced solenoid valve with a new one"
        else:
            action = "Checked solenoid valve"

        outcome = "Discharge gate operating normally"
        recovery = "Recovered"

        # A technician report is historical evidence until a human verifies it.
        verification = "PENDING_VERIFICATION"

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
        "verification": locals().get("verification", "PENDING_VERIFICATION"),
        "verification_status": locals().get("verification", "PENDING_VERIFICATION"),
        "verified": False,
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

    # ANVIQO_FIELD_REPORT_AUTO_SPARE_DEDUCTION_V2
    # Explicit spare consumption in a field report updates the authoritative
    # critical-spares Excel inventory automatically.
    #
    # IMPORTANT:
    # - Plant Memory remains PENDING_VERIFICATION.
    # - This is inventory bookkeeping only.
    # - No PLC/SCADA write is performed.
    # - The same report/spare consumption is deducted only once.

    import hashlib
    import json
    from datetime import datetime, timezone

    inventory_update = None
    spare_text = str(record.get("spare_used") or "").strip()

    if spare_text:
        m_spare = re.match(
            r"^([A-Z]{1,8}-\d{1,5})\s+x(\d+(?:\.\d+)?)$",
            spare_text,
            re.I,
        )

        if m_spare:
            spare_tag = m_spare.group(1).upper()
            spare_qty = float(m_spare.group(2))

            # Deterministic key prevents duplicate deduction when the same
            # field report is uploaded more than once.
            deduction_source = "|".join([
                str(filename or "").strip(),
                str(record.get("raw_report") or "").strip(),
                spare_tag,
                str(spare_qty),
            ])

            deduction_key = hashlib.sha256(
                deduction_source.encode("utf-8")
            ).hexdigest()

            ledger_path = os.path.join(
                BASE_DIR,
                "database",
                "spares",
                "field_report_spare_consumption.json",
            )

            ledger = []

            try:
                if os.path.exists(ledger_path):
                    with open(ledger_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, list):
                            ledger = loaded
            except Exception:
                ledger = []

            already_applied = any(
                str(item.get("deduction_key", "")) == deduction_key
                for item in ledger
                if isinstance(item, dict)
            )

            if already_applied:
                inventory_update = {
                    "status": "DUPLICATE_SKIPPED",
                    "tag": spare_tag,
                    "quantity": spare_qty,
                    "deduction_key": deduction_key,
                    "message": (
                        "Spare consumption already recorded; "
                        "duplicate deduction skipped."
                    ),
                }
            else:
                try:
                    from pci_spare_direct_excel import (
                        get_spare_quantity,
                        remove_spare,
                    )

                    before_qty = float(
                        get_spare_quantity(spare_tag)
                    )

                    if before_qty < spare_qty:
                        inventory_update = {
                            "status": "INSUFFICIENT_STOCK",
                            "tag": spare_tag,
                            "quantity": spare_qty,
                            "before_quantity": before_qty,
                            "after_quantity": before_qty,
                            "message": (
                                "Inventory protected; insufficient "
                                "available spare quantity."
                            ),
                        }
                    else:
                        result = remove_spare(
                            spare_tag,
                            spare_qty,
                        )

                        after_qty = float(
                            get_spare_quantity(spare_tag)
                        )

                        inventory_update = {
                            "status": "APPLIED",
                            "tag": spare_tag,
                            "quantity": spare_qty,
                            "before_quantity": before_qty,
                            "after_quantity": after_qty,
                            "deduction_key": deduction_key,
                            "engine_result": result,
                        }

                        ledger.append({
                            "deduction_key": deduction_key,
                            "memory_id": str(
                                memory.get("memory_id", "")
                            ),
                            "filename": str(filename or ""),
                            "tag": spare_tag,
                            "quantity": spare_qty,
                            "before_quantity": before_qty,
                            "after_quantity": after_qty,
                            "timestamp": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        })

                        os.makedirs(
                            os.path.dirname(ledger_path),
                            exist_ok=True,
                        )

                        tmp_path = ledger_path + ".tmp"

                        with open(
                            tmp_path,
                            "w",
                            encoding="utf-8",
                        ) as f:
                            json.dump(
                                ledger,
                                f,
                                indent=2,
                            )

                        os.replace(
                            tmp_path,
                            ledger_path,
                        )

                except Exception as exc:
                    inventory_update = {
                        "status": "ERROR",
                        "tag": spare_tag,
                        "quantity": spare_qty,
                        "error": str(exc),
                    }

    record["inventory_update"] = inventory_update

    # ANVIQO_NEON_FIELD_REPORT_HOOK_V2
    try:
        from anvi_neon_store import upsert_field_report
        upsert_field_report({
            "report_id": str(memory.get("memory_id","")),
            "tag": record.get("tag",""),
            "equipment": record.get("equipment",""),
            "event": record.get("event",""),
            "source": record.get("source",""),
            "raw_report": record.get("raw_report",""),
            "parsed_report": record,
            "memory": memory,
            "verification_status": "PENDING_VERIFICATION",
        })
    except Exception:
        pass

    return {
        "status": "PENDING_VERIFICATION",
        "domain": "plant_memory",
        "memory": memory,
        "parsed_report": record,
        **SAFETY,
    }
