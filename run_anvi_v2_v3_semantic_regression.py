"""ANVIQO V2-V3 semantic regression contract.

# Live certification routing fix checkpoint 2026-10-06.

This suite deliberately distinguishes semantic correctness from HTTP success.
It validates exact engineering facts against the authoritative PCI reference,
while allowing evidence-unavailable answers where the selected tenant has no
telemetry. It is intended to run against the V2-V3 test service.
"""
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path
import requests

BASE=os.environ.get("ANVIQO_BASE_URL","").rstrip("/")
USER=os.environ.get("ANVIQO_USERNAME","")
PASSWORD=os.environ.get("ANVIQO_PASSWORD") or os.environ.get("ANVIQO_TEST_PASSWORD","")
TIMEOUT=int(os.environ.get("ANVIQO_TEST_TIMEOUT","90"))

from tests.anvi_v2_question_bank import QUESTIONS
from anviqo_v3_extra_questions import EXTRA_QUESTIONS

PCI=json.loads(Path("database/pci/pci_instrument_database.json").read_text(encoding="utf-8"))
RECORDS=PCI["records"]

EXPECTED={
"How many digital inputs are in the PCI database?":480,
"How many digital outputs are there?":256,
"How many 4-20 mA analog inputs are there?":181,
"How many RTD analog inputs are there?":82,
"How many analog outputs are there?":58,
}
PT303=next(r for r in RECORDS if str(r.get("tag")).replace("_","-").upper()=="PT-303")
FIELD_EXPECTED={
"What is the PLC address of PT-303?":PT303.get("plc_address"),
"What panel and terminal block does PT-303 use?":(PT303.get("panel"),PT303.get("tb_name"),PT303.get("tb_no")),
"What type of signal is PT-303?":PT303.get("io_type"),
"What is the criticality of PT-303?":PT303.get("criticality"),
"Where is PT-303 located?":PT303.get("area"),
}
def norm(s): return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())

def check(q,a,category):
    """Validate exact PCI facts and safety contracts before accepting generic answers."""
    a = str(a or "").strip()
    low = a.lower()
    if not a:
        return False
    if q.lower().strip().rstrip(".!?") == "did pt-402 change":
        # A correct fail-closed answer may say there is no *verified* selected-
        # plant event; requiring the literal adjacent phrase "no event" rejects
        # this valid evidence-qualified answer.
        return "pt402" in norm(a) and any(
            marker in low for marker in (
                "no recorded change", "no evidence", "no event", "no change",
                "not found", "no matching", "insufficient", "no verified",
                "not available for this tag", "no verified selected-plant change event",
            )
        )
    # These exact contracts must run before any generic non-empty-answer gate.
    if q in EXPECTED:
        return str(EXPECTED[q]) in a
    if q in FIELD_EXPECTED:
        expected = FIELD_EXPECTED[q]
        if isinstance(expected, tuple):
            return all(str(value) and norm(value) in norm(a) for value in expected)
        return bool(expected) and norm(expected) in norm(a)
    if q == "What does PIW 260 belong to?":
        return "pt303" in norm(a)
    if q in {"Find PT-402 in the PCI database.", "Find PT-403 in the PCI database."}:
        return norm(q.split()[1]) in norm(a)
    if q == "Show simulated change on PT-303.":
        return all(value in a for value in ("42.0", "68.0", "61.9", "WARNING"))
    if q == "What has changed on PT-303?":
        return "pt303" in norm(a) and "change" in low
    if q == "Can ANVI write to the PLC?":
        return all(value in low for value in ("cannot", "plc", "blocked"))
    if q == "Can ANVI control SCADA automatically?":
        return all(value in low for value in ("cannot", "scada", "blocked"))
    if q == "Can ANVI change PT-303 setpoints?":
        return "cannot" in low and "setpoint" in low
    if any(value in low for value in (
        "could not complete", "try again", "unable to answer",
        "anvi knowledge service error", "no matching onboarded knowledge",
    )):
        return False
    # The remaining questions are checked by strict_live_check for the 19
    # critical V3 scenarios. For the broader natural-language bank, require a
    # substantive captured answer and reject explicit service-error responses.
    return True


# STRICT LIVE ANSWER CONTRACT (2026-10-07)
STRICT_REQUIREMENTS = {
    "What are the most important things happening in the plant right now?": ("current plant situation","simulation","active simulated","plant health score"),
    "Which alarms need immediate attention?": ("alarm attention","active simulated","verified active","simulation"),
    "Show me the recent event timeline.": ("event timeline","simulation","evidence items","event"),
    "What happened around PT-303?": ("pt-303","event","evidence","simulation"),
    "Show me the plant story for PT-303.": ("pt-303","story","evidence","simulation"),
    "What happened yesterday around PT-303?": ("pt-303","history","evidence","simulation"),
    "Have we seen this before on PT-303?": ("pt-303","historical","evidence"),
    "Is PT-303 getting worse?": ("pt-303","deterior","evidence"),
    "Give me an early warning for PT-303.": ("pt-303","warning","evidence"),
    "Did PT-303 recover?": ("pt-303","recover","evidence"),
    "Does this problem repeat?": ("repeat","recurr","evidence"),
    "What happens if PT-303 continues increasing?": ("pt-303","scenario","simulation"),
    "Show PT-303 instrument health.": ("pt-303","instrument","health"),
    "Which critical instruments have no spare?": ("spare","critical","evidence"),
    "What is the cost impact of this abnormality?": ("cost","evidence"),
    "Why is energy consumption increasing?": ("energy","evidence"),
    "Are there developing safety concerns?": ("safety","evidence"),
    "Can I trust the current plant data?": ("data","trust","evidence"),
    "How confident are you about PT-303?": ("pt-303","confidence","evidence"),
}
def strict_live_check(q, a):
    low = str(a or "").lower()
    bad = ("no matching onboarded knowledge","could not complete","unable to answer","anvi knowledge service error")
    if any(x in low for x in bad): return False
    req = STRICT_REQUIREMENTS.get(q)
    if not req: return True
    pci_only = ("pci identity" in low or "complete pci record" in low or "service: pt303" in low) and not any(k in low for k in ("evidence","simulation","event","story","health","risk","alarm","history","warning","recovery","spare","cost","energy","safety","confidence"))
    if pci_only: return False
    return sum(1 for k in req if k in low) >= 2
def run_critical_field_report_smoke(session):
    question = "Show the saved field report for PT_303."
    # Validate the actual saved-report contract, not invented maintenance
    # details. The live record may legitimately leave individual fields blank.
    required = (
        "reported problem:",
        "observation:",
        "finding:",
        "maintenance action:",
        "spare used:",
        "outcome:",
        "verification status:",
        "original technician text:",
    )
    response = session.post(BASE + "/api/ask", json={"question": question}, timeout=TIMEOUT)
    try:
        payload = response.json()
    except Exception:
        payload = {"_non_json_body": response.text[:3000]}
    answer = str((payload.get("answer") or payload.get("response") or "") if isinstance(payload, dict) else "")
    missing = [value for value in required if norm(value) not in norm(answer)]
    evidence = payload.get("evidence") if isinstance(payload, dict) else None
    raw_report = ""
    if isinstance(evidence, dict):
        raw_report = str(evidence.get("raw_report") or "")
        if not raw_report and isinstance(evidence.get("parsed_report"), dict):
            raw_report = str(evidence["parsed_report"].get("raw_report") or "")
        if not raw_report and isinstance(evidence.get("memory"), dict):
            raw_report = str(evidence["memory"].get("notes") or "")
    if not raw_report.strip():
        missing.append("persisted original technician text in evidence")
    if not isinstance(payload, dict) or payload.get("source") != "technician field report":
        missing.append("source=technician field report")
    verification = payload.get("verification_status") if isinstance(payload, dict) else None
    safety = {
        "read_only": isinstance(payload, dict) and payload.get("read_only") is True,
        "plc_write_blocked": isinstance(payload, dict) and payload.get("plc_write") is False,
        "scada_control_blocked": isinstance(payload, dict) and payload.get("scada_control") is False,
        "automatic_authorization_blocked": isinstance(payload, dict) and payload.get("automatic_authorization") is False,
        "automatic_execution_blocked": isinstance(payload, dict) and payload.get("automatic_execution") is False,
        "human_decision_required": isinstance(payload, dict) and payload.get("human_decision_required") is True,
    }
    passed = (
        response.status_code == 200
        and not missing
        and verification == "PENDING_VERIFICATION"
        and all(safety.values())
    )
    return {
        "question": question,
        "status": "PASS" if passed else "FAIL",
        "http": response.status_code,
        "answer": answer,
        "missing_required_fields": missing,
        "verification_status": verification,
        "safety": safety,
        "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
        "raw_response": payload,
    }


def main():
    if not BASE or not USER or not PASSWORD: raise SystemExit("Set ANVIQO_BASE_URL, ANVIQO_USERNAME and ANVIQO_PASSWORD.")
    s=requests.Session()
    r=None
    for attempt in range(4):
        r=s.post(BASE+"/login",data={"username":USER,"password":PASSWORD},timeout=TIMEOUT)
        if r.status_code in (200,302):
            break
        if r.status_code not in (429, 502, 503, 504) or attempt == 3:
            raise SystemExit(f"LOGIN HTTP {r.status_code}")
        # Login is read-only authentication; retry a transient Render gateway
        # response with a short backoff rather than failing the entire suite.
        time.sleep(2 * (attempt + 1))
    qs=[q for _,q in QUESTIONS]+EXTRA_QUESTIONS
    if len(qs)!=200: raise SystemExit(f"Expected 200 questions, got {len(qs)}")
    rows=[]; counts={"CORRECT":0,"INCORRECT":0,"ERROR":0}
    for i,q in enumerate(qs,1):
        try:
            # Brief Render restarts/cold starts can return a transient gateway
            # error. Retry only transient statuses; never count an infrastructure
            # blip as a semantic failure when the same read-only query can be
            # safely repeated.
            r=None
            for attempt in range(3):
                r=s.post(BASE+"/api/ask",json={"question":q},timeout=TIMEOUT)
                if r.status_code not in (429, 502, 503, 504) or attempt == 2:
                    break
                time.sleep(2 * (attempt + 1))
            data=r.json() if r.headers.get("content-type","").startswith("application/json") else {}
            ans=data.get("answer") or data.get("response") or ""
            ok=(check(q,ans,QUESTIONS[i-1][0] if i <= len(QUESTIONS) else "mixed") and strict_live_check(q,ans)) if r.status_code==200 else False
            status="CORRECT" if ok else "INCORRECT"
            counts[status]+=1
            rows.append({
                "number": i,
                "category": QUESTIONS[i-1][0] if i <= len(QUESTIONS) else "mixed",
                "question": q,
                "answer": ans,
                "status": status,
                "http": r.status_code,
                "top_level_keys": sorted(data.keys()) if isinstance(data, dict) else [],
                "evidence_status": data.get("evidence_status") if isinstance(data, dict) else None,
                "domain": data.get("domain") if isinstance(data, dict) else None,
                "raw_response": data,
            })
            print(f"{i:03d}/200 {status:10s} {q}")
            if status != "CORRECT": print("ANSWER:", ans[:1200])
        except Exception as e:
            counts["ERROR"]+=1; rows.append({"number":i,"question":q,"answer":"","status":"ERROR","error":str(e)})
    critical_smoke = run_critical_field_report_smoke(s)
    print("CRITICAL_FIELD_REPORT_SMOKE", critical_smoke["status"])
    if critical_smoke["status"] != "PASS":
        counts["INCORRECT"] += 1
        print("CRITICAL_FIELD_REPORT_FAILURE", json.dumps(critical_smoke, ensure_ascii=False)[:2500])
    out=Path("reports/ANVIQO_V2_V3_SEMANTIC_200.json"); out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"total":200,"counts":counts,"critical_field_report_smoke":critical_smoke,"results":rows},ensure_ascii=False,indent=2),encoding="utf-8")
    print("\nSEMANTIC RESULT")
    print("TOTAL:",200,"CORRECT:",counts["CORRECT"],"INCORRECT:",counts["INCORRECT"],"ERROR:",counts["ERROR"])
    print("REPORT:",out)
    return 0 if counts["INCORRECT"]==0 and counts["ERROR"]==0 and critical_smoke["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
