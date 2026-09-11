"""ANVIQO field-report runtime bridge.

Keeps field-report handling outside frozen V5 intelligence. Inventory changes
only when the universal industrial language layer identifies explicit spare
consumption. Query/read paths remain read-only and verification remains human.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from anvi_industrial_language import extract_spare_usage as understand_spare_usage

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "database" / "spares" / "field_report_spare_sync.json"
_TAG_RE = re.compile(r"\b([A-Z]{1,8}[-_ ]?\d{1,5})\b", re.I)
_NUM_WORDS = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}

def _utc_now(): return datetime.now(timezone.utc).isoformat()

def _load_ledger():
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if not LEDGER.exists(): return {"version":"FIELD-REPORT-SPARE-SYNC-1.0","records":[]}
    try:
        data=json.loads(LEDGER.read_text(encoding="utf-8"))
        if not isinstance(data,dict) or not isinstance(data.get("records"),list): raise ValueError
        return data
    except Exception: return {"version":"FIELD-REPORT-SPARE-SYNC-1.0","records":[]}

def _save_ledger(data):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    tmp=LEDGER.with_suffix(".tmp")
    tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    tmp.replace(LEDGER)

def _normalise_tag(tag):
    return str(tag or "").strip().upper().replace("_","-").replace(" ","-")

def extract_spare_usage(parsed_report: dict) -> tuple[str,float] | None:
    """Use the universal industrial language layer across all report fields."""
    if not isinstance(parsed_report,dict): return None
    sources=(parsed_report.get("spare_used"),parsed_report.get("raw_report"),parsed_report.get("maintenance_action"))
    for value in sources:
        usage=understand_spare_usage(str(value or ""))
        if usage: return usage
    combined=" ".join(str(x or "") for x in sources if x)
    usage=understand_spare_usage(combined)
    return usage

def _already_applied(report_id,tag,quantity):
    data=_load_ledger()
    for row in data["records"]:
        if (str(row.get("report_id"))==str(report_id) and _normalise_tag(row.get("tag"))==_normalise_tag(tag) and float(row.get("quantity",0))==float(quantity) and row.get("status")=="APPLIED"):
            return row
    return None

def sync_field_report_spare(parsed_report: dict, report_id: str) -> dict:
    usage=extract_spare_usage(parsed_report)
    if not usage:
        return {"status":"NOT_APPLICABLE","inventory_changed":False,"message":"No explicit spare-used/consumed statement was found."}
    tag,quantity=usage
    report_id=str(report_id or "").strip()
    if not report_id: raise ValueError("Field report memory ID is required for inventory sync.")
    existing=_already_applied(report_id,tag,quantity)
    if existing:
        return {"status":"ALREADY_APPLIED","inventory_changed":False,"tag":tag,"quantity":quantity,"before":existing.get("before"),"after":existing.get("after"),"transaction_id":existing.get("transaction_id"),"report_id":report_id}
    from pci_spare_direct_excel import remove_spare
    result=remove_spare(tag,quantity)
    data=_load_ledger()
    data["records"].append({"report_id":report_id,"tag":tag,"quantity":quantity,"before":result["before"],"after":result["after"],"transaction_id":result["transaction_id"],"status":"APPLIED","source":"technician field report","timestamp_utc":_utc_now()})
    _save_ledger(data)
    return {"status":"APPLIED","inventory_changed":True,"tag":tag,"quantity":quantity,"before":result["before"],"after":result["after"],"transaction_id":result["transaction_id"],"report_id":report_id,"message":f"Field report recorded {quantity:g} used {tag}; critical-spare Excel quantity reduced from {result['before']:g} to {result['after']:g}."}

def _report_query(q):
    """Detect report-history questions without stealing ordinary spare commands.

    The Phase-2 bridge runs before /api/ask. Therefore terms such as
    "replaced" or "spare used" alone are not sufficient to classify a request
    as a field-report query: those phrases are also valid live inventory or
    maintenance commands. A report/history marker is required unless the
    wording is explicitly historical.
    """
    low=str(q or "").strip().lower()
    if not low:
        return False

    explicit_report = (
        "field report" in low
        or "field reports" in low
        or "technician report" in low
        or "technician reports" in low
        or "operator report" in low
        or "operator reports" in low
        or "maintenance history" in low
        or "previous report" in low
        or "previous reports" in low
    )

    historical = (
        "what happened" in low
        or "last time" in low
        or "previously" in low
        or "earlier" in low
        or "reported" in low
        or "what was done before" in low
        or "what did maintenance find" in low
        or "what did the technician find" in low
    )

    return explicit_report or historical

def _has_report_details(report):
    if not isinstance(report,dict): return False
    return any(str(report.get(k) or "").strip() for k in ("observation","finding","maintenance_action","outcome","recovery_status","spare_used","raw_report","notes"))

def answer_field_report_query(question):
    if not _report_query(question): return None
    import plant_memory
    tag_match=_TAG_RE.search(str(question or ""))
    tag=_normalise_tag(tag_match.group(1)) if tag_match else ""
    results=plant_memory.search_all_memory(query=question,tag=tag,limit=10)
    reports=[r for r in results if r.get("source")=="technician field report" and _has_report_details(r)]
    if not reports: return None
    report=reports[0]
    pending=report.get("verification_status")!="VERIFIED"
    usage=extract_spare_usage(report)
    display_spare=report.get("spare_used") or ""
    if usage:
        spare_tag,spare_qty=usage
        display_spare=f"{spare_tag} x {spare_qty:g}"
    answer=(f"I found a technician field report for {report.get('tag') or report.get('equipment') or 'the equipment'}. "
            f"Observation: {report.get('observation') or 'not stated'}. "
            f"Finding: {report.get('finding') or 'not stated'}. "
            f"Maintenance action: {report.get('maintenance_action') or 'not stated'}. "
            f"Outcome: {report.get('outcome') or 'not stated'}. "
            f"Spare used: {display_spare or 'none reported'}.")
    if pending: answer += " This is a human field report and remains PENDING_VERIFICATION."
    return {"answer":answer,"status":"OK","domain":"plant_memory","source":"technician field report","memory_id":report.get("memory_id",""),"verification_status":report.get("verification_status","PENDING_VERIFICATION"),"evidence":report,"read_only":True,"plc_write":False,"scada_control":False}
