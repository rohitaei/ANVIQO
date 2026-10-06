"""ANVIQO V2→V3 extraordinary operator/engineer intelligence.

Universal, tenant-scoped, evidence-first reference layer. Read-only toward OT.
No causal claim is emitted without evidence; recommendations never execute.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Any

SAFETY = {
    "read_only": True, "plc_write": False, "scada_control": False,
    "automatic_authorization": False, "automatic_execution": False,
    "human_decision_required": True, "causation_claim": False,
}

def _tenant(points, events, org, plant):
    ps=[p for p in points if getattr(p,"organization_id","") == org and getattr(p,"plant_id","") == plant]
    es=[e for e in events if getattr(e,"organization_id","") == org and getattr(e,"plant_id","") == plant]
    return ps, es

class ExtraordinaryOperatorIntelligence:
    def __init__(self, platform):
        self.platform=platform

    def _data(self, org, plant):
        return self.platform._points_for(org,plant), self.platform._events_for(org,plant)

    def attention_now(self, org, plant):
        points,events=self._data(org,plant)
        alarms=[e for e in events if e.event_type=="ALARM"]
        critical=[e for e in alarms if e.severity=="CRITICAL"]
        warning=[e for e in alarms if e.severity=="WARNING"]
        changed=self.platform.what_changed(org,plant).get("changes",[])
        ranked=[]
        for e in critical: ranked.append({"priority":"P1","tag":e.tag or e.equipment,"reason":e.message,"evidence":"ALARM"})
        for e in warning: ranked.append({"priority":"P2","tag":e.tag or e.equipment,"reason":e.message,"evidence":"ALARM"})
        for c in changed[:10]: ranked.append({"priority":"P3","tag":c["tag"],"reason":"value changed","evidence":"TELEMETRY_CHANGE"})
        return {"status":"OK","headline":f"{len(ranked)} attention item(s)","items":ranked[:20],
                "evidence_status":"EVIDENCE_AVAILABLE" if ranked else "NO_EVIDENCE","safety":dict(SAFETY)}

    def plant_story(self, org, plant, tag=None):
        points,events=self._data(org,plant)
        if tag: points=[p for p in points if p.tag==tag]; events=[e for e in events if e.tag==tag or e.equipment==tag]
        timeline=[]
        for p in points: timeline.append((p.timestamp,{"kind":"TELEMETRY","tag":p.tag,"value":p.value,"quality":p.quality,"source":p.source}))
        for e in events: timeline.append((e.timestamp,{"kind":e.event_type,"tag":e.tag,"equipment":e.equipment,"severity":e.severity,"message":e.message,"source":e.source}))
        timeline.sort(key=lambda x:x[0])
        return {"status":"OK","tag":tag,"timeline":[v for _,v in timeline[-100:]],
                "story_rule":"chronological evidence only; correlation is not causation",
                "evidence_status":"EVIDENCE_AVAILABLE" if timeline else "NO_EVIDENCE","safety":dict(SAFETY)}

    def time_machine(self, org, plant, start, end, tag=None):
        try:
            s=datetime.fromisoformat(start.replace("Z","+00:00")); e=datetime.fromisoformat(end.replace("Z","+00:00"))
        except Exception:
            return {"status":"BAD_REQUEST","message":"Use ISO-8601 timestamps.","safety":dict(SAFETY)}
        points,events=self._data(org,plant)
        points=[p for p in points if s<=p.timestamp<=e and (tag is None or p.tag==tag)]
        events=[x for x in events if s<=x.timestamp<=e and (tag is None or x.tag==tag or x.equipment==tag)]
        return {"status":"OK","window":{"start":start,"end":end},"tag":tag,
                "telemetry":[{"tag":p.tag,"timestamp":p.timestamp.isoformat(),"value":p.value,"quality":p.quality} for p in points],
                "events":[{"timestamp":x.timestamp.isoformat(),"event_type":x.event_type,"tag":x.tag,"severity":x.severity,"message":x.message} for x in events],
                "evidence_status":"EVIDENCE_AVAILABLE" if points or events else "NO_EVIDENCE","safety":dict(SAFETY)}

    def plant_memory(self, org, plant, tag=None):
        points,events=self._data(org,plant)
        groups=Counter()
        for e in events:
            if e.severity in {"WARNING","CRITICAL"}: groups[e.tag or e.equipment or "UNKNOWN"] += 1
        return {"status":"OK","similar_history":[{"tag":k,"occurrences":v} for k,v in groups.most_common(20) if tag is None or k==tag],
                "history_available":bool(groups),"evidence_status":"EVIDENCE_AVAILABLE" if groups else "NO_EVIDENCE",
                "causation_claimed":False,"safety":dict(SAFETY)}

    def anomaly_search(self, org, plant):
        points,events=self._data(org,plant); out=[]
        grouped=defaultdict(list)
        for p in points:
            if isinstance(p.value,(int,float)): grouped[p.tag].append(float(p.value))
        for tag,vals in grouped.items():
            if len(vals)>=3:
                avg=mean(vals[:-1])
                if avg and abs(vals[-1]-avg)/abs(avg)>=0.10:
                    out.append({"tag":tag,"latest":vals[-1],"prior_average":avg,"deviation_ratio":abs(vals[-1]-avg)/abs(avg)})
        return {"status":"OK","anomalies":sorted(out,key=lambda x:-x["deviation_ratio"])[:50],
                "evidence_status":"EVIDENCE_AVAILABLE" if out else "NO_EVIDENCE","safety":dict(SAFETY)}

    def deterioration(self, org, plant, tag):
        points,_=self._data(org,plant); vals=[float(p.value) for p in points if p.tag==tag and isinstance(p.value,(int,float))]
        if len(vals)<3: return {"status":"NO DATA","tag":tag,"trend":"INSUFFICIENT_EVIDENCE","evidence_status":"NO_EVIDENCE","safety":dict(SAFETY)}
        direction="INCREASING" if vals[-1]>vals[0] else ("DECREASING" if vals[-1]<vals[0] else "FLAT")
        return {"status":"OK","tag":tag,"trend":direction,"change":vals[-1]-vals[0],"sample_count":len(vals),
                "deterioration_claimed":False,"evidence_status":"EVIDENCE_AVAILABLE","safety":dict(SAFETY)}

    def early_warning(self, org, plant, tag):
        d=self.deterioration(org,plant,tag)
        if d.get("status")!="OK": return d
        return {"status":"OK","tag":tag,"early_warning":d["trend"]!="FLAT",
                "basis":{"trend":d["trend"],"change":d["change"]},"not_an_alarm":True,
                "evidence_status":"EVIDENCE_AVAILABLE","safety":dict(SAFETY)}

    def recovery(self, org, plant, tag):
        points,events=self._data(org,plant)
        related=[e for e in events if e.tag==tag or e.equipment==tag]
        values=[p for p in points if p.tag==tag and isinstance(p.value,(int,float))]
        return {"status":"OK","tag":tag,"event_count":len(related),"latest_value":values[-1].value if values else None,
                "recovery_status":"EVIDENCE_REQUIRES_COMPARISON_TO_BASELINE",
                "evidence_status":"EVIDENCE_AVAILABLE" if related or values else "NO_EVIDENCE","safety":dict(SAFETY)}

    def recurring_problems(self, org, plant):
        _,events=self._data(org,plant); c=Counter((e.tag or e.equipment or "UNKNOWN") for e in events if e.severity in {"WARNING","CRITICAL"})
        return {"status":"OK","recurring":[{"tag":k,"occurrences":v} for k,v in c.most_common(20) if v>1],
                "recurrence_proven":False,"evidence_status":"EVIDENCE_AVAILABLE" if c else "NO_EVIDENCE","safety":dict(SAFETY)}

    def shift_handover(self, org, plant):
        return self.platform.shift(org,plant) | {"handover":"DRAFT — HUMAN REVIEW REQUIRED","automatic_distribution":False}

    def historical_similarity(self, org, plant, tag):
        return self.plant_memory(org,plant,tag) | {"comparison":"event-history similarity only","causation_claimed":False}

    def what_if(self, org, plant, tag, steps=5):
        points,_=self._data(org,plant); vals=[float(p.value) for p in points if p.tag==tag and isinstance(p.value,(int,float))]
        if not vals: return {"status":"NO DATA","tag":tag,"simulation":True,"safety":dict(SAFETY)}
        last=vals[-1]; delta=(last-vals[-2]) if len(vals)>1 else 0.0
        scenario=[last+delta*i for i in range(1,max(2,min(int(steps),20))+1)]
        return {"status":"SIMULATION","tag":tag,"current":last,"step_delta":delta,"projected_values":scenario,
                "simulation_only":True,"no_control_action":True,"safety":dict(SAFETY)}

    def instrument_health(self, org, plant, tag):
        return self.platform.instrument(org,plant,tag) | {"health_model":"signal quality + flatline + baseline deviation","calibration_claimed":False}

    def spare_intelligence(self, org, plant):
        return self.platform.maintenance(org,plant) | {"spare_decision":"inventory evidence must be checked before recommendation","automatic_execution":False}

    def cost_of_abnormality(self, org, plant):
        return {"status":"OK","status_message":"Cost model requires plant production/energy/cost evidence.",
                "metrics":[],"cost_estimate_claimed":False,"evidence_status":"NO_EVIDENCE","safety":dict(SAFETY)}

    def energy_intelligence(self, org, plant, tags=()):
        return self.platform.energy_production_quality(org,plant,tags) | {"optimization_claimed":False,"recommendation_execution":False}

    def safety_intelligence(self, org, plant):
        a=self.platform.alarms(org,plant)
        return {"status":"OK","critical_alarms":a["critical_count"],"warning_alarms":a["warning_count"],
                "human_attention_required":a["critical_count"]>0,"safety":dict(SAFETY)}

    def ot_data_trust(self, org, plant):
        points,_=self._data(org,plant)
        return {"status":"OK","points":len(points),"bad_quality":sum(getattr(p,"quality","").upper() in {"BAD","UNCERTAIN"} for p in points),
                "telemetry_trust":"LIMITED" if any(getattr(p,"quality","").upper() in {"BAD","UNCERTAIN"} for p in points) else ("AVAILABLE" if points else "NO_DATA"),
                "write_path":"BLOCKED","safety":dict(SAFETY)}

    def confidence(self, org, plant, tag=None):
        points,events=self._data(org,plant)
        evidence=len([p for p in points if tag is None or p.tag==tag])+len([e for e in events if tag is None or e.tag==tag or e.equipment==tag])
        level="HIGH" if evidence>=5 else ("MEDIUM" if evidence>=2 else "LOW")
        return {"status":"OK","tag":tag,"evidence_count":evidence,"evidence_strength":level,
                "causal_claimed":False,"safety":dict(SAFETY)}

def register(app, platform):
    from flask import jsonify, request
    engine=ExtraordinaryOperatorIntelligence(platform)
    def scope():
        from flask import session
        org,plant=session.get("organization_id",""),session.get("plant_id","")
        if not org or not plant: return None
        return org,plant
    def call(fn,*args,**kwargs):
        s=scope()
        if not s: return jsonify({"status":"TENANT_UNAVAILABLE","safety":dict(SAFETY)}),409
        return jsonify(fn(*s,*args,**kwargs))
    @app.get("/api/v3/intelligence/attention"); 
    def attention(): return call(engine.attention_now)
    @app.get("/api/v3/intelligence/story")
    def story(): return call(engine.plant_story,request.args.get("tag"))
    @app.get("/api/v3/intelligence/time-machine")
    def tm(): return call(engine.time_machine,request.args.get("start",""),request.args.get("end",""),request.args.get("tag"))
    @app.get("/api/v3/intelligence/memory")
    def memory(): return call(engine.plant_memory,request.args.get("tag"))
    @app.get("/api/v3/intelligence/anomalies")
    def anomalies(): return call(engine.anomaly_search)
    @app.get("/api/v3/intelligence/deterioration/<tag>")
    def deterioration(tag): return call(engine.deterioration,tag)
    @app.get("/api/v3/intelligence/early-warning/<tag>")
    def early(tag): return call(engine.early_warning,tag)
    @app.get("/api/v3/intelligence/recovery/<tag>")
    def recovery(tag): return call(engine.recovery,tag)
    @app.get("/api/v3/intelligence/recurring")
    def recurring(): return call(engine.recurring_problems)
    @app.get("/api/v3/intelligence/handover")
    def handover(): return call(engine.shift_handover)
    @app.get("/api/v3/intelligence/similarity/<tag>")
    def similarity(tag): return call(engine.historical_similarity,tag)
    @app.get("/api/v3/intelligence/what-if/<tag>")
    def whatif(tag): return call(engine.what_if,tag,request.args.get("steps",5))
    @app.get("/api/v3/intelligence/instrument-health/<tag>")
    def ih(tag): return call(engine.instrument_health,tag)
    @app.get("/api/v3/intelligence/spares")
    def spares(): return call(engine.spare_intelligence)
    @app.get("/api/v3/intelligence/cost")
    def cost(): return call(engine.cost_of_abnormality)
    @app.get("/api/v3/intelligence/energy")
    def energy(): return call(engine.energy_intelligence,[x for x in request.args.get("tags","").split(",") if x])
    @app.get("/api/v3/intelligence/safety")
    def safety(): return call(engine.safety_intelligence)
    @app.get("/api/v3/intelligence/ot-trust")
    def ot(): return call(engine.ot_data_trust)
    @app.get("/api/v3/intelligence/confidence")
    def confidence(): return call(engine.confidence,request.args.get("tag"))
