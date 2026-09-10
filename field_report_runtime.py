"""ANVIQO field-report runtime bridge.

Keeps field-report handling outside the frozen V5 intelligence modules.
Responsibilities:
- Apply an explicitly reported spare usage to the authoritative Excel stock.
- Make the operation idempotent per stored field-report memory ID.
- Provide a deterministic read path for later field-report questions.

A report only changes inventory when the report explicitly states a spare was
used/consumed. Mere mention of a spare does not change stock.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "database" / "spares" / "field_report_spare_sync.json"

_TAG_RE = re.compile(r"\b([A-Z]{1,8}[-_ ]?\d{1,5})\b", re.I)
_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _load_ledger():
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if not LEDGER.exists():
        return {"version": "FIELD-REPORT-SPARE-SYNC-1.0", "records": []}
    try:
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("records"), list):
            raise ValueError
        return data
    except Exception:
        return {"version": "FIELD-REPORT-SPARE-SYNC-1.0", "records": []}


def _save_ledger(data):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(LEDGER)


def _normalise_tag(tag):
    return str(tag or "").strip().upper().replace("_", "-").replace(" ", "-")


def extract_spare_usage(parsed_report: dict) -> tuple[str, float] | None:
    """Return (tag, quantity) only for explicit spare-used language."""
    text = str(parsed_report.get("spare_used") or "").strip()
    raw = str(parsed_report.get("raw_report") or "").strip()
    combined = " ".join(x for x in (text, raw) if x)

    m = re.search(r"\b([A-Z]{1,8}[-_ ]?\d{1,5})\s*x\s*(\d+(?:\.\d+)?)\b", text, re.I)
    if m:
        return _normalise_tag(m.group(1)), float(m.group(2))

    patterns = [
        r"\b(?:used|consumed|removed)\s+(?P<qty>one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)\s+(?P<tag>[A-Z]{1,8}[-_ ]?\d{1,5})\s+spares?\b",
        r"\b(?P<qty>one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)\s+(?P<tag>[A-Z]{1,8}[-_ ]?\d{1,5})\s+spares?\s+(?:used|consumed|removed)\b",
        r"\b(?P<tag>[A-Z]{1,8}[-_ ]?\d{1,5})\s+spare\s+(?:used|consumed|removed)\b",
        # Common technician wording: "replaced by new PT-303 1 no spare used".
        # This explicitly identifies the replacement spare and its quantity.
        r"\breplaced\s+by\s+(?:a|an|new\s+)?(?P<tag>[A-Z]{1,8}[-_ ]?\d{1,5})\s+(?P<qty>one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)\s+nos?\s+spare\s+used\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, combined, re.I)
        if m:
            qty = m.groupdict().get("qty") or "1"
            qty = _NUM_WORDS.get(qty.lower(), qty)
            return _normalise_tag(m.group("tag")), float(qty)

    if text and re.search(r"\b(?:used|consumed|removed)\b", text, re.I):
        tag_match = _TAG_RE.search(text)
        if tag_match:
            qty_match = re.search(r"\b(\d+(?:\.\d+)?)\b", text)
            return _normalise_tag(tag_match.group(1)), float(qty_match.group(1) if qty_match else 1)

    return None


def _already_applied(report_id: str, tag: str, quantity: float):
    data = _load_ledger()
    for row in data["records"]:
        if (
            str(row.get("report_id")) == str(report_id)
            and _normalise_tag(row.get("tag")) == _normalise_tag(tag)
            and float(row.get("quantity", 0)) == float(quantity)
            and row.get("status") == "APPLIED"
        ):
            return row
    return None


def sync_field_report_spare(parsed_report: dict, report_id: str) -> dict:
    usage = extract_spare_usage(parsed_report)
    if not usage:
        return {
            "status": "NOT_APPLICABLE",
            "inventory_changed": False,
            "message": "No explicit spare-used/consumed statement was found.",
        }

    tag, quantity = usage
    report_id = str(report_id or "").strip()
    if not report_id:
        raise ValueError("Field report memory ID is required for inventory sync.")

    existing = _already_applied(report_id, tag, quantity)
    if existing:
        return {
            "status": "ALREADY_APPLIED",
            "inventory_changed": False,
            "tag": tag,
            "quantity": quantity,
            "before": existing.get("before"),
            "after": existing.get("after"),
            "transaction_id": existing.get("transaction_id"),
            "report_id": report_id,
        }

    from pci_spare_direct_excel import remove_spare

    result = remove_spare(tag, quantity)

    data = _load_ledger()
    ledger_row = {
        "report_id": report_id,
        "tag": tag,
        "quantity": quantity,
        "before": result["before"],
        "after": result["after"],
        "transaction_id": result["transaction_id"],
        "status": "APPLIED",
        "source": "technician field report",
        "timestamp_utc": _utc_now(),
    }
    data["records"].append(ledger_row)
    _save_ledger(data)

    return {
        "status": "APPLIED",
        "inventory_changed": True,
        "tag": tag,
        "quantity": quantity,
        "before": result["before"],
        "after": result["after"],
        "transaction_id": result["transaction_id"],
        "report_id": report_id,
        "message": f"Field report recorded {quantity:g} used {tag}; critical-spare Excel quantity reduced from {result['before']:g} to {result['after']:g}.",
    }


def _report_query(q: str) -> bool:
    low = str(q or "").lower()
    triggers = (
        "field report", "field reports", "technician report", "operator report",
        "maintenance history", "what happened", "last time", "previous report",
        "reported", "replaced", "replacement", "spare used", "spare consumed",
    )
    return any(x in low for x in triggers)


def _has_report_details(report: dict) -> bool:
    """Reject empty placeholder records so they cannot hide real persistence."""
    if not isinstance(report, dict):
        return False
    fields = (
        "observation", "finding", "maintenance_action", "outcome",
        "recovery_status", "spare_used", "raw_report", "notes",
    )
    return any(str(report.get(key) or "").strip() for key in fields)


def answer_field_report_query(question: str):
    """Return a grounded field-report answer or None when not a report query."""
    if not _report_query(question):
        return None

    import plant_memory

    tag_match = _TAG_RE.search(str(question or ""))
    tag = _normalise_tag(tag_match.group(1)) if tag_match else ""
    results = plant_memory.search_all_memory(query=question, tag=tag, limit=10)
    reports = [
        r for r in results
        if r.get("source") == "technician field report" and _has_report_details(r)
    ]

    if not reports:
        return None

    report = reports[0]
    pending = report.get("verification_status") != "VERIFIED"

    # Normalize spare usage at read time as well as at ingest time. This is
    # important for older human reports whose parser stored the raw sentence
    # but left the structured spare_used field empty. Never change inventory
    # here; this path is strictly read-only.
    usage = extract_spare_usage(report)
    display_spare = report.get("spare_used") or ""
    if usage:
        spare_tag, spare_qty = usage
        display_spare = f"{spare_tag} x {spare_qty:g}"

    answer = (
        f"I found a technician field report for {report.get('tag') or report.get('equipment') or 'the equipment'}. "
        f"Observation: {report.get('observation') or 'not stated'}. "
        f"Finding: {report.get('finding') or 'not stated'}. "
        f"Maintenance action: {report.get('maintenance_action') or 'not stated'}. "
        f"Outcome: {report.get('outcome') or 'not stated'}. "
        f"Spare used: {display_spare or 'none reported'}."
    )
    if pending:
        answer += " This is a human field report and remains PENDING_VERIFICATION."

    return {
        "answer": answer,
        "status": "OK",
        "domain": "plant_memory",
        "source": "technician field report",
        "memory_id": report.get("memory_id", ""),
        "verification_status": report.get("verification_status", "PENDING_VERIFICATION"),
        "evidence": report,
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
    }
