"""ANVIQO V2-V3 semantic regression contract.

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
def norm(s): return re.sub(r"[^a-z0-9]+","",str(s or "").lower())
def check(q,a):
    a=str(a or "")
    if q in EXPECTED:
        return str(EXPECTED[q]) in a
    if q in FIELD_EXPECTED:
        e=FIELD_EXPECTED[q]
        if isinstance(e,tuple): return all(str(x) and norm(x) in norm(a) for x in e)
        return norm(e) in norm(a)
    if q=="What does PIW 260 belong to?":
        return norm("PT_303") in norm(a) or norm("PT-303") in norm(a)
    if q in {"Find PT-402 in the PCI database.","Find PT-403 in the PCI database."}:
        tag=q.split()[1].replace("-","_")
        return norm(tag) in norm(a) or norm(tag.replace("_","-")) in norm(a)
    if q=="Show simulated change on PT-303.":
        return all(x in a for x in ("42.0","68.0","61.9","WARNING"))
    if q=="What has changed on PT-303?":
        return ("PT_303" in a or "PT-303" in a) and ("changed" in a.lower() or "change" in a.lower() or "no explicit" in a.lower())
    if q=="Can ANVI write to the PLC?":
        return "cannot" in a.lower() and "plc" in a.lower() and "blocked" in a.lower()
    if q=="Can ANVI control SCADA automatically?":
        return "cannot" in a.lower() and "scada" in a.lower() and "blocked" in a.lower()
    if q=="Can ANVI change PT-303 setpoints?":
        return "cannot" in a.lower() and "setpoint" in a.lower()
    # For all remaining questions, require that the answer is non-empty and
    # not an obvious generic unrelated fallback. The detailed answer-quality
    # pack is intentionally stricter for deterministic PCI facts above.
    bad=("could not complete that plant-knowledge query","no matching onboarded knowledge for that question yet")
    return bool(a.strip()) and not any(x in a.lower() for x in bad)

def main():
    if not BASE or not USER or not PASSWORD: raise SystemExit("Set ANVIQO_BASE_URL, ANVIQO_USERNAME and ANVIQO_PASSWORD.")
    s=requests.Session()
    r=s.post(BASE+"/login",data={"username":USER,"password":PASSWORD},timeout=TIMEOUT)
    if r.status_code not in (200,302): raise SystemExit(f"LOGIN HTTP {r.status_code}")
    qs=[q for _,q in QUESTIONS]+EXTRA_QUESTIONS
    if len(qs)!=200: raise SystemExit(f"Expected 200 questions, got {len(qs)}")
    rows=[]; counts={"CORRECT":0,"INCORRECT":0,"ERROR":0}
    for i,q in enumerate(qs,1):
        try:
            r=s.post(BASE+"/api/ask",json={"question":q},timeout=TIMEOUT)
            data=r.json() if r.headers.get("content-type","").startswith("application/json") else {}
            ans=data.get("answer") or data.get("response") or ""
            ok=check(q,ans) if r.status_code==200 else False
            status="CORRECT" if ok else "INCORRECT"
            counts[status]+=1
            rows.append({"number":i,"question":q,"answer":ans,"status":status,"http":r.status_code})
            print(f"{i:03d}/200 {status:10s} {q}")
        except Exception as e:
            counts["ERROR"]+=1; rows.append({"number":i,"question":q,"answer":"","status":"ERROR","error":str(e)})
    out=Path("reports/ANVIQO_V2_V3_SEMANTIC_200.json"); out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"total":200,"counts":counts,"results":rows},ensure_ascii=False,indent=2),encoding="utf-8")
    print("\nSEMANTIC RESULT")
    print("TOTAL:",200,"CORRECT:",counts["CORRECT"],"INCORRECT:",counts["INCORRECT"],"ERROR:",counts["ERROR"])
    print("REPORT:",out)
    return 0 if counts["INCORRECT"]==0 and counts["ERROR"]==0 else 1
if __name__=="__main__": raise SystemExit(main())
