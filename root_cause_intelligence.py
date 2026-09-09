"""ANVIQO Root Cause Intelligence V1.3.
Evidence-backed diagnostic assessment and correlation over existing ANVIQO engines.
No PLC writes, SCADA control, automatic execution, or unverified causation.
"""
from __future__ import annotations
import importlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

VERSION = "ANVIQO-RCI-V1.3"
SAFETY = {"control_mode":"READ_ONLY","plc_write":False,"scada_control":False,"automatic_execution":False,"human_decision_required":True}
_EQUIPMENT_RE = re.compile(r"\b(?:PT|FT|LT|TT|DP|MCV|SOV|FSV|PCV|POSR|TCV|FV|XV|CV)\s*[-_ ]?\s*\d{1,5}\b", re.I)
_TEXT_KEYS = ("message","event","observation","finding","maintenance_action","outcome","confirmation_evidence","notes")


def is_root_cause_query(query: str) -> bool:
    q=" ".join(str(query or "").strip().lower().split())
    if not q or not _EQUIPMENT_RE.search(q): return False
    cause=("root cause","cause of","causing","reason for","why is","why was","why did","why has","what caused","failure cause","fault cause","why does","why are","why were")
    symptom=("abnormal","failure","failed","fault","problem","issue","trip","unhealthy","malfunction","not working","stopped")
    return any(x in q for x in cause) and (any(x in q for x in symptom) or any(x in q for x in ("why is","why was","why did","why has","why does","why are","why were")) or "root cause" in q or "what caused" in q)


def _load(name:str):
    try: return importlib.import_module(name)
    except Exception: return None


def _call(module,function,*args,**kwargs):
    if module is None: return None
    fn=getattr(module,function,None)
    if not callable(fn): return None
    try: return fn(*args,**kwargs)
    except Exception: return None


def _norm_tag(tag:str)->str:
    value=str(tag or "").strip().upper(); m=_EQUIPMENT_RE.search(value)
    if m: value=m.group(0)
    return re.sub(r"[^A-Z0-9]","",value)


def _tag_variants(tag:str)->List[str]:
    canonical=str(tag or "").strip().upper().replace("_","-").replace(" ","-")
    m=re.match(r"^([A-Z]+)-?(\d{1,5})$",canonical)
    if not m: return [canonical] if canonical else []
    p,n=m.groups(); return [f"{p}-{n}",f"{p}_{n}",f"{p} {n}",f"{p}{n}"]


def extract_tag(text:str)->Optional[str]:
    m=_EQUIPMENT_RE.search(str(text or ""))
    if not m: return None
    return re.sub(r"\s*[-_ ]\s*","-",m.group(0).upper())


def _verified_memory(tag:str)->List[Dict[str,Any]]:
    records=_call(_load("plant_memory"),"search_all_memory",query="",limit=1000)
    if not isinstance(records,list): return []
    wanted=_norm_tag(tag); out=[]
    for r in records:
        if not isinstance(r,dict) or _norm_tag(r.get("tag"))!=wanted or r.get("source")!="technician field report": continue
        if r.get("verified") is True or str(r.get("verification_status","")).upper()=="VERIFIED" or r.get("human_verified") is True: out.append(r)
    return out


def _events(tag:str)->List[Dict[str,Any]]:
    module=_load("event_timeline")
    if module is None: return []
    out=[]; seen=set()
    for variant in _tag_variants(tag):
        events=_call(module,"get_events",variant)
        if not isinstance(events,list): continue
        for e in events:
            if not isinstance(e,dict): continue
            key=(e.get("timestamp"),e.get("event_type"),e.get("message"))
            if key not in seen: seen.add(key); out.append(e)
    out.sort(key=lambda e:str(e.get("timestamp") or ""))
    return out


def _health(tag:str):
    module=_load("equipment_health")
    for variant in _tag_variants(tag):
        result=_call(module,"get_latest_health",variant)
        if result is not None: return result
    return None


def _pci_evidence(tag:str,query:str)->Dict[str,Any]:
    module=_load("pci_conversation")
    if module is None: return {"identity":None,"live":None,"answer":None}
    identity=None
    for variant in _tag_variants(tag):
        identity=_call(module,"find_tag",variant)
        if identity is not None: break
    live=None; snapshot=_call(module,"get_live_pci_snapshot")
    if isinstance(snapshot,dict):
        wanted=_norm_tag(tag)
        points=snapshot.get("points",[])
        for p in points if isinstance(points,list) else []:
            if isinstance(p,dict) and _norm_tag(p.get("tag"))==wanted: live=p; break
    return {"identity":identity,"live":live,"answer":_call(module,"answer",query)}


def _maintenance(tag:str,query:str):
    module=_load("maintenance_experience_matching"); context={"equipment":tag,"tag":tag,"query":query}
    matching=_call(module,"find_matching_experience",context)
    if not isinstance(matching,list): matching=[]
    return _call(module,"build_experience_context",context), matching


def _text(records:List[Dict[str,Any]])->str:
    return " ".join(str(r.get(k) or "") for r in records for k in _TEXT_KEYS).lower()


def _record_text(record:Dict[str,Any])->str:
    return " ".join(str(record.get(k) or "") for k in _TEXT_KEYS).strip()


def _hypotheses(events,memory,health,pci_live=None)->List[Dict[str,Any]]:
    combined=f"{_text(events)} {_text(memory)}"
    rules=[
      ("instrument-air / positioner issue","air pressure" in combined and ("valve position" in combined or "positioner" in combined),"Explicit evidence links instrument-air/valve-position information in available history."),
      ("sensor / transmitter signal issue",any(x in combined for x in ("transmitter fault","sensor fault","signal fault","signal failure","instrument fault")),"A verified event or field finding explicitly records a sensor/transmitter/instrument fault."),
      ("wiring / termination issue",any(x in combined for x in ("loose terminal","loose wiring","termination fault","cable fault","broken wire")),"A verified event or field finding explicitly records a wiring/termination problem."),
      ("power-supply issue",any(x in combined for x in ("fuse blown","fuse failure","power supply fault","24v failure","24 v failure","supply failure")),"A verified event or field finding explicitly records a power/fuse/supply problem."),
      ("process-condition contribution",any(x in combined for x in ("process pressure","process temperature","flow abnormal","high temperature","low pressure")),"The available evidence contains an explicit process-condition abnormality that may contribute to the observed symptom."),
    ]
    out=[]
    for name,matched,rationale in rules:
        if not matched: continue
        ev=[]
        for source,records in (("EVENT_TIMELINE",events),("VERIFIED_PLANT_MEMORY",memory)):
            for r in records:
                raw=_record_text(r)
                if raw: ev.append({"source":source,"memory_id":r.get("memory_id"),"timestamp":r.get("timestamp"),"text":raw})
        out.append({"hypothesis":name,"status":"INVESTIGATE","support":rationale,"evidence":ev})
    return out


def _event_detail(event:Dict[str,Any])->Dict[str,Any]:
    return {"timestamp":event.get("timestamp"),"event_type":event.get("event_type"),"severity":event.get("severity"),"message":event.get("message"),"data":event.get("data") or {}}


def _correlate(tag:str,live:Optional[Dict[str,Any]],events:List[Dict[str,Any]],memory:List[Dict[str,Any]],matching:List[Any])->Dict[str,Any]:
    active_event = bool(live and live.get("event_active") is True)
    timeline_details=[_event_detail(e) for e in events]
    field_details=[]
    for r in memory:
        field_details.append({"memory_id":r.get("memory_id"),"timestamp":r.get("timestamp"),"event":r.get("event"),"observation":r.get("observation"),"finding":r.get("finding"),"maintenance_action":r.get("maintenance_action"),"outcome":r.get("outcome"),"confirmation_evidence":r.get("confirmation_evidence")})
    maintenance_details=[]
    for item in matching:
        if isinstance(item,dict): maintenance_details.append(item)
        else: maintenance_details.append({"text":str(item)})
    if timeline_details:
        active_description=timeline_details[-1]
    elif active_event:
        active_description={"status":"ACTIVE_SIGNAL_ONLY","message":"The PCI stream marks an active event, but no event-detail record is available in Event Timeline."}
    else:
        active_description=None
    recent=[]
    for e in timeline_details[-5:]: recent.append({"source":"EVENT_TIMELINE",**e})
    for r in field_details[-5:]: recent.append({"source":"VERIFIED_PLANT_MEMORY",**r})
    recent.sort(key=lambda x:str(x.get("timestamp") or ""))
    correlation_status="CORRELATED_EVIDENCE" if len(recent)>=2 else ("EVENT_AVAILABLE" if recent else ("ACTIVE_EVENT_UNDETAILLED" if active_event else "NO_CORRELATED_HISTORY"))
    missing=[]
    if not timeline_details: missing.append("No Event Timeline detail is available for this tag.")
    if not memory: missing.append("No verified field-report history is available for this tag.")
    if not maintenance_details: missing.append("No matching maintenance experience is available.")
    if active_event and not timeline_details: missing.append("The live stream reports event_active=True, but the event type/message is unavailable from the current event source.")
    return {"status":correlation_status,"active_event":active_description,"recent_changes":recent,"event_timeline":timeline_details,"verified_field_history":field_details,"maintenance_observations":maintenance_details,"missing_evidence":missing}


def _observed_condition(tag,query,pci,health,events,memory):
    live=pci.get("live") if isinstance(pci,dict) else None
    result={"tag":tag,"reported_symptom":any(x in str(query).lower() for x in ("abnormal","fault","failure","issue","problem","unhealthy","malfunction","stopped")),"live_state":None,"live_value":None,"changed":None,"event_active":None,"mode":None,"source":None,"evidence_basis":[]}
    if isinstance(live,dict):
        for k in ("state","value","changed","event_active","mode","source"): result["live_"+k if k in ("state","value") else k]=live.get(k)
        if live.get("state") in ("WARNING","CRITICAL"): result["evidence_basis"].append(f"PCI stream currently reports state {live.get('state')}.")
        if live.get("changed") is True: result["evidence_basis"].append("PCI stream currently marks the point as changed.")
        if live.get("event_active") is True: result["evidence_basis"].append("PCI stream currently marks an active event.")
    if isinstance(health,dict): result["evidence_basis"].append("Equipment health context is available.")
    if events: result["evidence_basis"].append(f"{len(events)} event-timeline record(s) are available.")
    if memory: result["evidence_basis"].append(f"{len(memory)} verified field-report record(s) are available.")
    return result


def build_root_cause_intelligence(query:str,tag:Optional[str]=None)->Dict[str,Any]:
    query=str(query or "").strip(); tag=extract_tag(tag or query) or _norm_tag(tag or "")
    events=_events(tag) if tag else []; memory=_verified_memory(tag) if tag else []; health=_health(tag) if tag else None
    pci=_pci_evidence(tag,query) if tag else {"identity":None,"live":None,"answer":None}; experience,matching=_maintenance(tag,query) if tag else (None,[])
    live=pci.get("live") if isinstance(pci,dict) else None
    observed=_observed_condition(tag,query,pci,health,events,memory)
    hypotheses=_hypotheses(events,memory,health if isinstance(health,dict) else {},live)
    correlation=_correlate(tag,live,events,memory,matching)
    identity_available=pci.get("identity") is not None; live_available=live is not None
    any_evidence=bool(events or memory or health or identity_available or live_available or experience or matching)
    if hypotheses:
        status="HYPOTHESES_AVAILABLE"; conclusion="ANVIQO found evidence-supported hypotheses to investigate. These are not confirmed root causes."
    elif isinstance(live,dict) and live.get("state") in ("WARNING","CRITICAL"):
        status="INSUFFICIENT_EVIDENCE"
        state=live.get("state"); mode=live.get("mode","SIMULATION")
        event_text=correlation["active_event"].get("message") if isinstance(correlation.get("active_event"),dict) else None
        if event_text:
            conclusion=(f"{tag} is currently {state} in the PCI {mode} stream at value {live.get('value')}. "
                        f"Correlated event evidence: {event_text} Root cause is not confirmed.")
        elif correlation["active_event"]:
            conclusion=(f"{tag} is currently {state} in the PCI {mode} stream at value {live.get('value')}. "
                        "The stream reports an active event, but no event-detail record is available. Root cause is not confirmed.")
        else:
            conclusion=(f"{tag} is currently {state} in the PCI {mode} stream at value {live.get('value')}. "
                        "No correlated causal evidence is available to confirm a root cause. Root cause is not confirmed.")
    elif any_evidence:
        status="INSUFFICIENT_EVIDENCE"; conclusion="ANVIQO identified equipment evidence, but not enough explicit causal evidence to confirm a root cause."
    else:
        status="NO_EVIDENCE"; conclusion="No usable equipment evidence was found for a root-cause assessment."
    return {"rci_version":VERSION,"timestamp":datetime.now(timezone.utc).isoformat(),"query":query,"tag":tag,"status":status,"conclusion":conclusion,
      "observed_condition":observed,"correlation":correlation,"hypotheses":hypotheses,
      "evidence":{"pci_identity":pci.get("identity"),"pci_live":live,"pci_answer":pci.get("answer"),"events":events,"verified_plant_memory":memory,"health":health,"maintenance_experience":experience,"matching_experience":matching},
      "evidence_summary":{"event_count":len(events),"verified_memory_count":len(memory),"health_available":health is not None,"pci_identity_available":identity_available,"pci_live_available":live_available,"maintenance_experience_available":experience is not None or bool(matching),"matching_experience_count":len(matching),"current_live_state":live.get("state") if isinstance(live,dict) else None,"current_live_changed":live.get("changed") if isinstance(live,dict) else None,"current_live_event_active":live.get("event_active") if isinstance(live,dict) else None,"correlation_status":correlation.get("status")},
      "safety":dict(SAFETY),"decision_status":"HUMAN_DECISION_REQUIRED"}
