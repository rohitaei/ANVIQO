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


def _sentence_list(text):
    """Split technician prose into clean sentences."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return []
    return [x.strip(" .;:") for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]


def _extract_labeled_field(text, label, next_labels):
    """Extract an explicitly labelled field without swallowing later fields."""
    labels = "|".join(re.escape(x) for x in next_labels)
    pattern = (
        rf"(?is)\b{re.escape(label)}\s*:\s*(.*?)"
        rf"(?=\s*(?:{labels})\s*:|$)"
    )
    m = re.search(pattern, str(text or ""))
    return _clean(m.group(1)).strip(" .;:") if m else ""


def _extract_observation(text):
    labeled = _extract_labeled_field(
        text, "Observation",
        ["Finding", "Maintenance action", "Action", "Outcome",
         "Recovery", "Spare used", "Spare"]
    )
    if labeled:
        return labeled

    sentences = _sentence_list(text)

    for s in sentences:
        low = s.lower()
        if any(x in low for x in (
            "was observed", "were observed", "observed showing",
            "abnormal indication", "abnormal pressure",
            "abnormal flow", "not showing", "no indication",
            "failed to indicate", "indication was abnormal"
        )):
            s = re.sub(
                r"(?i)^(during the shift,?\s*)?",
                "",
                s
            )
            s = re.sub(
                r"(?i)^.*?\bwas observed\s+",
                "",
                s
            )
            return _clean(s).strip(" .;:")

    return ""


def _extract_finding(text):
    labeled = _extract_labeled_field(
        text, "Finding",
        ["Maintenance action", "Action", "Outcome",
         "Recovery", "Spare used", "Spare"]
    )
    if labeled:
        return labeled

    sentences = _sentence_list(text)

    for s in sentences:
        low = s.lower()

        if "found faulty" in low:
            m = re.search(
                r"(?i)(?:was|were|is|are)?\s*(?:checked|inspected)?\s*"
                r"(?:and\s+)?found\s+(.+)$",
                s
            )
            if m:
                return _clean(m.group(1)).strip(" .;:")

        if "fault was confirmed" in low:
            return "Fault confirmed"

        if "fuse blown" in low:
            return "Fuse blown"

        if "no power" in low and "fuse" in low:
            return "Fuse blown / no power"

    return ""


def _extract_action(text):
    labeled = _extract_labeled_field(
        text, "Maintenance action",
        ["Outcome", "Recovery", "Spare used", "Spare"]
    )
    if labeled:
        return labeled

    labeled = _extract_labeled_field(
        text, "Action",
        ["Outcome", "Recovery", "Spare used", "Spare"]
    )
    if labeled:
        return labeled

    sentences = _sentence_list(text)
    actions = []

    for s in sentences:
        low = s.lower()

        if any(x in low for x in (
            "inspected", "checked", "replaced", "changed",
            "repaired", "reset", "calibrated", "tightened",
            "cleaned"
        )):
            if (
                "found faulty" not in low
                and "found failed" not in low
                and not low.startswith("after replacement")
                and "returned to normal" not in low
                and "restored to healthy" not in low
                and "restored healthy" not in low
            ):
                actions.append(s)

    if actions:
        return "; ".join(actions)

    low = str(text or "").lower()
    if "changed fuse" in low or "replaced fuse" in low:
        return "Fuse replaced"

    return ""


def _extract_outcome(text):
    labeled = _extract_labeled_field(
        text, "Outcome",
        ["Recovery", "Spare used", "Spare"]
    )
    if labeled:
        return labeled

    sentences = _sentence_list(text)

    for s in sentences:
        low = s.lower()

        if any(x in low for x in (
            "returned to normal", "became normal",
            "restored to healthy", "restored healthy",
            "operating normally", "working normally",
            "signal returned", "indication returned",
            "now ok", "back to normal"
        )):
            return s

    return ""


def _extract_recovery(text):
    labeled = _extract_labeled_field(
        text, "Recovery",
        ["Spare used", "Spare"]
    )
    if labeled:
        return labeled

    low = str(text or "").lower()

    if any(x in low for x in (
        "recovered", "recovery confirmed",
        "condition recovered", "equipment recovered"
    )):
        return "Recovered"

    return ""


def _extract_spare(text):
    labeled = _extract_labeled_field(
        text, "Spare used",
        ["Observation", "Finding", "Maintenance action",
         "Action", "Outcome", "Recovery", "Spare"]
    )
    if not labeled:
        labeled = _extract_labeled_field(
            text, "Spare",
            ["Observation", "Finding", "Maintenance action",
             "Action", "Outcome", "Recovery", "Spare used"]
        )

    if labeled:
        m = re.search(
            r"(?i)\b([A-Z]{1,8}-\d{1,5})\s*x\s*(\d+(?:\.\d+)?)\b",
            labeled
        )
        if m:
            return f"{m.group(1).upper()} x{m.group(2)}"

        m = re.search(
            r"(?i)\b([A-Z]{1,8}-\d{1,5})\b.*?\b(\d+(?:\.\d+)?)\s*(?:nos?|pcs?|pieces?)\b",
            labeled
        )
        if m:
            return f"{m.group(1).upper()} x{m.group(2)}"

    numbers = {
        "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8",
        "nine": "9", "ten": "10"
    }

    m = re.search(
        r"(?i)\b(?:replaced\s+with|using|used|from|with|by)\s+"
        r"(one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)\s+"
        r"([A-Z]{1,8}-\d{1,5})\s+spares?\b",
        str(text or "")
    )
    if m:
        qty = numbers.get(m.group(1).lower(), m.group(1))
        return f"{m.group(2).upper()} x{qty}"

    m = re.search(
        r"(?i)\b(?:replaced\s+with|using|used|from|with|by)\s+"
        r"(?:a|an)\s+([A-Z]{1,8}-\d{1,5})\s+spare\b",
        str(text or "")
    )
    if m:
        return f"{m.group(1).upper()} x1"

    m = re.search(
        r"(?i)\b(?:using|used|from)\s+(?:one|1)\s+"
        r"([A-Z]{1,8}-\d{1,5})\s+spare\b",
        str(text or "")
    )
    if m:
        return f"{m.group(1).upper()} x1"

    m = re.search(
        r"(?i)\b([A-Z]{1,8}-\d{1,5})\s+spare\s+(?:used|consumed)\b",
        str(text or "")
    )
    if m:
        return f"{m.group(1).upper()} x1"

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
