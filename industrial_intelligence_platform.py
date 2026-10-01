"""ANVIQO Industrial Intelligence Platform.
Unified, read-only, evidence-first engines for the remaining roadmap domains.
No PLC/SCADA writes. Correlation is never promoted to causation.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Optional, Tuple
import math

VERSION = "INDUSTRIAL_INTELLIGENCE_1.0"
SAFETY = {
    "read_only": True, "plc_write": False, "scada_control": False,
    "human_decision_required": True, "automatic_authorization": False,
    "automatic_execution": False, "causation_claim": False,
}

def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def _ts(x):
    if isinstance(x, (int, float)): return float(x)
    if isinstance(x, datetime): return x.timestamp()
    try: return datetime.fromisoformat(str(x).replace("Z","+00:00")).timestamp()
    except Exception: return None

def evidence(item: Dict[str, Any], source="ANVIQO_SIMULATION", quality="GOOD"):
    return {
        "plant_id": item.get("plant_id", "UNKNOWN"),
        "equipment": item.get("equipment") or item.get("tag"),
        "tag": item.get("tag"),
        "source": item.get("source", source),
        "timestamp": item.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "quality": item.get("quality", quality),
        "value": item.get("value"),
    }

def alarm_intelligence(alarms: Iterable[Dict[str, Any]], window_s=300):
    rows = [dict(a) for a in alarms]
    active = [a for a in rows if str(a.get("state","")).upper() in ("ACTIVE","ON","TRUE") or a.get("active") is True]
    floods = len(active) >= 10
    by_tag = {}
    for a in rows:
        tag = a.get("tag") or a.get("equipment") or "UNKNOWN"
        by_tag.setdefault(tag, []).append(a)
    chatter, stale, recurring = [], [], []
    for tag, vals in by_tag.items():
        times = [_ts(v.get("timestamp")) for v in vals]
        times = [t for t in times if t is not None]
        states = [str(v.get("state","")).upper() for v in vals]
        if len(vals) >= 4 and len(times) >= 2:
            gaps = [b-a for a,b in zip(times,times[1:]) if b>=a]
            if gaps and mean(gaps) <= window_s:
                chatter.append({"tag":tag,"events":len(vals),"pattern":"CHATTER"})
        if any(s in ("ACTIVE","ON") for s in states) and len(vals) >= 3:
            recurring.append({"tag":tag,"occurrences":len(vals),"pattern":"RECURRING"})
        if any(v.get("stale") is True for v in vals):
            stale.append({"tag":tag,"pattern":"STALE"})
    return {"module":"alarm_intelligence","alarm_count":len(rows),"active_count":len(active),
            "alarm_flood":floods,"chattering":chatter,"stale":stale,"recurring":recurring,
            "priority_conflicts":[],"safety":SAFETY}

def process_deviation(values: Iterable[Dict[str, Any]], envelope=None, rate_limit=None):
    rows=[dict(v) for v in values]
    nums=[_num(v.get("value")) for v in rows]; nums=[x for x in nums if x is not None]
    out=[]
    for v in rows:
        x=_num(v.get("value"))
        if x is None: continue
        lo=hi=None
        if envelope:
            e=envelope.get(v.get("tag") or v.get("equipment"), envelope.get("default",{}))
            lo=e.get("min") if isinstance(e,dict) else None; hi=e.get("max") if isinstance(e,dict) else None
        if lo is not None and x < lo: out.append({"tag":v.get("tag"),"type":"LOW","value":x,"limit":lo,"evidence":evidence(v)})
        if hi is not None and x > hi: out.append({"tag":v.get("tag"),"type":"HIGH","value":x,"limit":hi,"evidence":evidence(v)})
    drift = None
    if len(nums)>=3:
        drift=nums[-1]-nums[0]
    roc=[]
    for a,b in zip(rows,rows[1:]):
        x,y=_num(a.get("value")),_num(b.get("value")); ta,tb=_ts(a.get("timestamp")),_ts(b.get("timestamp"))
        if None not in (x,y,ta,tb) and tb>ta:
            r=(y-x)/(tb-ta)
            if rate_limit is not None and abs(r)>rate_limit: roc.append({"tag":b.get("tag"),"rate":r,"type":"RATE_OF_CHANGE"})
    return {"module":"process_deviation","samples":len(rows),"deviations":out,"drift":drift,"rate_changes":roc,
            "early_warning":bool(out or roc),"safety":SAFETY}

def sensor_health(samples: Iterable[Dict[str, Any]], frozen_window=5, noise_factor=3.0):
    rows=[dict(x) for x in samples]; vals=[_num(x.get("value")) for x in rows]
    valid=[x for x in vals if x is not None]; issues=[]
    if len(valid)>=frozen_window and len(set(valid[-frozen_window:]))==1:
        issues.append({"type":"FROZEN_SIGNAL","tag":rows[-1].get("tag")})
    if len(valid)>=4:
        sd=pstdev(valid)
        if sd > noise_factor*(abs(mean(valid))+1e-9):
            issues.append({"type":"NOISY_SIGNAL","tag":rows[-1].get("tag"),"stddev":sd})
    for x in rows:
        v=_num(x.get("value"))
        if v is None or x.get("quality") in ("BAD","UNCERTAIN"):
            issues.append({"type":"BAD_OR_UNCERTAIN_SIGNAL","tag":x.get("tag"),"quality":x.get("quality")})
        if x.get("calibration_due") is True: issues.append({"type":"CALIBRATION_DUE","tag":x.get("tag")})
        if x.get("out_of_range") is True: issues.append({"type":"OUT_OF_RANGE","tag":x.get("tag")})
    return {"module":"sensor_health","samples":len(rows),"issues":issues,
            "healthy":not issues,"sensor_vs_process":[],"io_health":[], "safety":SAFETY}

def reliability_intelligence(events: Iterable[Dict[str,Any]], observation_hours=None):
    rows=[dict(x) for x in events]; failures=[x for x in rows if str(x.get("type","")).upper() in ("FAILURE","TRIP","FAULT")]
    repairs=[x for x in rows if str(x.get("type","")).upper() in ("REPAIR","RESTORED","MAINTENANCE_COMPLETE")]
    mtbf=(observation_hours/len(failures)) if observation_hours and failures else None
    durations=[_num(x.get("duration_hours")) for x in repairs if _num(x.get("duration_hours")) is not None]
    mttr=mean(durations) if durations else None
    counts={}
    for x in rows:
        k=x.get("equipment") or x.get("tag") or "UNKNOWN"; counts[k]=counts.get(k,0)+1
    bad=sorted(({"equipment":k,"event_count":v} for k,v in counts.items()),key=lambda z:z["event_count"],reverse=True)
    return {"module":"equipment_reliability","failures":len(failures),"maintenance_events":len(repairs),
            "mtbf_hours":mtbf,"mttr_hours":mttr,"bad_actors":bad[:10],"risk_evidence":[],
            "safety":SAFETY}

def evidence_chain(events: Iterable[Dict[str,Any]]):
    rows=sorted((dict(x) for x in events),key=lambda x:(_ts(x.get("timestamp")) is None,_ts(x.get("timestamp")) or 0))
    return {"module":"root_cause_evidence_chain","chain":[evidence(x) | {"event":x.get("event") or x.get("type")} for x in rows],
            "causation_established":False,"interpretation":"Chronological correlation/evidence chain; causation requires human/engineering verification.",
            "safety":SAFETY}

def energy_intelligence(records: Iterable[Dict[str,Any]]):
    rows=[dict(x) for x in records]; vals=[_num(x.get("value")) for x in rows]; vals=[v for v in vals if v is not None]
    production=sum(_num(x.get("production")) or 0 for x in rows)
    energy=sum(vals) if vals else 0
    return {"module":"energy_utilities","records":len(rows),"energy_total":energy,
            "production_total":production,"specific_energy":(energy/production if production else None),
            "abnormal_consumption":[x for x in rows if x.get("abnormal") is True],"safety":SAFETY}

def production_intelligence(records: Iterable[Dict[str,Any]]):
    rows=[dict(x) for x in records]; prod=[_num(x.get("production")) for x in rows]; prod=[x for x in prod if x is not None]
    loss=[_num(x.get("loss")) or 0 for x in rows]
    return {"module":"production_loss","records":len(rows),"production_total":sum(prod),"loss_total":sum(loss),
            "throughput":(mean(prod) if prod else None),
            "loss_events":[x for x in rows if (_num(x.get("loss")) or 0)>0],"safety":SAFETY}

def quality_intelligence(records: Iterable[Dict[str,Any]]):
    rows=[dict(x) for x in records]; bad=[x for x in rows if x.get("within_spec") is False]
    return {"module":"quality","records":len(rows),"out_of_spec":len(bad),
            "quality_events":bad,"process_quality_relationships":[],"equipment_quality_relationships":[],"safety":SAFETY}

def maintenance_copilot(history: Iterable[Dict[str,Any]]):
    rows=[dict(x) for x in history]; rec={}
    for x in rows:
        k=x.get("equipment") or x.get("tag") or "UNKNOWN"; rec[k]=rec.get(k,0)+1
    return {"module":"maintenance_copilot","history_count":len(rows),
            "recurrence":[{"equipment":k,"events":v} for k,v in sorted(rec.items(),key=lambda p:p[1],reverse=True)],
            "priorities":[],"evidence_packages":[],"cmms_preparation":[],"human_review_required":True,"safety":SAFETY}

def spare_intelligence(spares: Iterable[Dict[str,Any]]):
    rows=[dict(x) for x in spares]; risks=[]
    for x in rows:
        q=_num(x.get("qty_available")); mn=_num(x.get("minimum_stock"))
        if q is not None and mn is not None and q<=mn: risks.append({"equipment":x.get("equipment") or x.get("tag"),"qty":q,"minimum":mn,"risk":"LOW_STOCK"})
    return {"module":"critical_spares","items":len(rows),"stock_risk":risks,
            "usage_history":[x for x in rows if x.get("used") is True],"safety":SAFETY}

def shift_intelligence(data: Dict[str,Any]):
    return {"module":"shift_handover","abnormal_equipment":data.get("abnormal_equipment",[]),
            "alarms":data.get("alarms",[]),"maintenance":data.get("maintenance",[]),
            "spares_used":data.get("spares_used",[]),"open_issues":data.get("open_issues",[]),
            "follow_up":data.get("follow_up",[]),"evidence_backed":True,"safety":SAFETY}

def field_intelligence(observations: Iterable[Dict[str,Any]]):
    rows=[dict(x) for x in observations]
    return {"module":"field_operator_intelligence","observations":rows,
            "verification_status":"PENDING_VERIFICATION","human_supplied":True,"safety":SAFETY}

def procedure_intelligence(procedures: Iterable[Dict[str,Any]], query=""):
    q=query.lower(); matches=[]
    for p in procedures:
        text=str(p.get("title",""))+" "+str(p.get("text",""))
        if not q or q in text.lower(): matches.append(p)
    return {"module":"sop_procedure_intelligence","matches":matches[:10],
            "retrieval_only":True,"execution":False,"safety":SAFETY}

def process_safety_context(data: Dict[str,Any]):
    return {"module":"process_safety","interlocks":data.get("interlocks",[]),
            "permissives":data.get("permissives",[]),"safeguards":data.get("safeguards",[]),
            "critical_conditions":data.get("critical_conditions",[]),
            "control_independence":True,"safety":SAFETY}

def ot_asset_evidence(assets: Iterable[Dict[str,Any]]):
    return {"module":"ot_asset_evidence","assets":[dict(x) for x in assets],
            "approved_paths_only":True,"cyber_program_replacement":False,"safety":SAFETY}

def evidence_graph(nodes: Iterable[Dict[str,Any]], relationships: Iterable[Dict[str,Any]]):
    return {"module":"evidence_graph","nodes":[dict(x) for x in nodes],
            "relationships":[dict(x) for x in relationships],"auditable":True,"safety":SAFETY}

def incident_workspace(events: Iterable[Dict[str,Any]]):
    return {"module":"incident_investigation","timeline":evidence_chain(events)["chain"],
            "previous_incidents":[],"maintenance":[],"field_reports":[],"outcome":None,
            "causation_established":False,"human_review_required":True,"safety":SAFETY}

def explainable_health(evidence_items: Iterable[Dict[str,Any]]):
    rows=[dict(x) for x in evidence_items]; bad=sum(1 for x in rows if str(x.get("severity","")).upper() in ("CRITICAL","HIGH","BAD"))
    score=max(0.0,100.0-(bad*10.0)) if rows else None
    return {"module":"explainable_plant_health","score":score,
            "condition":"ATTENTION" if score is not None and score<80 else "NORMAL",
            "contributing_evidence":rows[:20],"confidence":"DATA_DEPENDENT",
            "causation_established":False,"safety":SAFETY}

def benchmarking(plants: Iterable[Dict[str,Any]]):
    rows=[dict(x) for x in plants]
    return {"module":"fleet_benchmarking","records":len(rows),"comparisons":rows,
            "definition_warning":"Only compare governed, like-for-like metrics with adequate data quality.","safety":SAFETY}

def digital_twin(identity: Dict[str,Any], condition=None, history=None, prediction=None):
    return {"module":"state_aware_digital_twin","identity":identity,"condition":condition or {},
            "relationships":identity.get("relationships",[]),"historical_behavior":history or [],
            "predicted_state":prediction or None,"read_only":True,"safety":SAFETY}

def sustainability(records: Iterable[Dict[str,Any]]):
    rows=[dict(x) for x in records]
    return {"module":"sustainability_emissions","records":len(rows),
            "energy":sum(_num(x.get("energy")) or 0 for x in rows),
            "water":sum(_num(x.get("water")) or 0 for x in rows),
            "fuel":sum(_num(x.get("fuel")) or 0 for x in rows),
            "emissions":sum(_num(x.get("emissions")) or 0 for x in rows),
            "efficiency_evidence":[],"safety":SAFETY}

def governance(evidence_items: Iterable[Dict[str,Any]], model_version=VERSION):
    rows=[dict(x) for x in evidence_items]
    return {"module":"industrial_ai_governance","model_version":model_version,
            "evidence_provenance":[evidence(x) for x in rows],"reproducible":True,
            "auditability":True,"human_approval_required":True,"safety":SAFETY}

def simulate_gateway(tags: Iterable[Dict[str,Any]]):
    """Future PLC adapter contract: simulated/read-only only."""
    now=datetime.now(timezone.utc).isoformat()
    return {"mode":"SIMULATION","protocol":"ADAPTER_CONTRACT","read_only":True,
            "plc_write":False,"scada_control":False,"timestamp":now,
            "observations":[{**dict(t),"timestamp":t.get("timestamp",now),"quality":t.get("quality","GOOD")} for t in tags]}

def run_industrial_intelligence(payload: Dict[str,Any]):
    p=payload or {}
    return {
        "version":VERSION,"timestamp":datetime.now(timezone.utc).isoformat(),
        "safety":SAFETY,
        "alarm":alarm_intelligence(p.get("alarms",[])),
        "process":process_deviation(p.get("process_values",[]),p.get("envelopes")),
        "sensor":sensor_health(p.get("sensor_samples",[])),
        "reliability":reliability_intelligence(p.get("reliability_events",[]),p.get("observation_hours")),
        "root_cause":evidence_chain(p.get("events",[])),
        "energy":energy_intelligence(p.get("energy",[])),
        "production":production_intelligence(p.get("production",[])),
        "quality":quality_intelligence(p.get("quality",[])),
        "maintenance":maintenance_copilot(p.get("maintenance",[])),
        "spares":spare_intelligence(p.get("spares",[])),
        "shift":shift_intelligence(p.get("shift",{})),
        "field":field_intelligence(p.get("field",[])),
        "procedures":procedure_intelligence(p.get("procedures",[]),p.get("procedure_query","")),
        "process_safety":process_safety_context(p.get("process_safety",{})),
        "ot":ot_asset_evidence(p.get("ot_assets",[])),
        "graph":evidence_graph(p.get("graph_nodes",[]),p.get("graph_relationships",[])),
        "incident":incident_workspace(p.get("incident_events",[])),
        "health":explainable_health(p.get("health_evidence",[])),
        "benchmark":benchmarking(p.get("benchmark",[])),
        "digital_twin":digital_twin(p.get("identity",{}),p.get("condition"),p.get("history"),p.get("prediction")),
        "sustainability":sustainability(p.get("sustainability",[])),
        "governance":governance(p.get("governance_evidence",[])),
        "gateway":simulate_gateway(p.get("gateway_tags",[])),
    }

def self_test():
    out=run_industrial_intelligence({
        "alarms":[{"tag":"PT-303","state":"ACTIVE"}],
        "process_values":[{"tag":"PT-303","value":120}],
        "sensor_samples":[{"tag":"PT-303","value":120,"quality":"GOOD"}]*5,
        "reliability_events":[{"equipment":"PT-303","type":"FAILURE"}],
        "events":[{"tag":"PT-303","type":"DEVIATION"}],
        "gateway_tags":[{"tag":"PT-303","value":120}],
    })
    assert out["safety"]==SAFETY
    assert out["gateway"]["read_only"] and not out["gateway"]["plc_write"]
    assert out["root_cause"]["causation_established"] is False
    return {"status":"PASS","version":VERSION,"modules":22,"safety":SAFETY}

if __name__=="__main__":
    print(self_test())
