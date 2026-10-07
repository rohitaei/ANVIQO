"""ANVIQO V3.5→V4 Enterprise Evidence Federation and Management boundary."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib,json,os,sqlite3,threading

SAFETY={"read_only":True,"plc_write":False,"scada_control":False,"automatic_authorization":False,"automatic_execution":False,"human_decision_required":True,"causation_claim":False,"cross_plant_fallback":False}
SOURCES={"PLC_EDGE","OPC_UA","MQTT","SPARKPLUG","MODBUS_TCP","HISTORIAN","CMMS","EAM","SAP","API","OPERATOR"}

@dataclass(frozen=True)
class IntegrationSource:
    source_id:str; source_type:str; organization_id:str; plant_id:str
    enabled:bool=True; read_only:bool=True; trust_class:str="UNVERIFIED"

class EnterpriseEvidenceStore:
    def __init__(self,path=None):
        self.path=path or os.getenv("ANVIQO_V4_ENTERPRISE_DB","/tmp/anviqo_v4_enterprise.db")
        self.lock=threading.RLock(); self._init()
    def db(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def _init(self):
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS sources(source_id TEXT PRIMARY KEY,organization_id TEXT,plant_id TEXT,source_type TEXT,enabled INTEGER,read_only INTEGER,trust_class TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS evidence(evidence_id TEXT PRIMARY KEY,organization_id TEXT,plant_id TEXT,source_id TEXT,source_type TEXT,subject_type TEXT,subject_id TEXT,observed_at TEXT,payload TEXT,quality TEXT,lineage TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS audit(audit_id TEXT PRIMARY KEY,organization_id TEXT,plant_id TEXT,action TEXT,object_id TEXT,actor TEXT,timestamp TEXT,detail TEXT)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_ev_scope ON evidence(organization_id,plant_id,observed_at)")
            c.execute("CREATE INDEX IF NOT EXISTS ix_audit_scope ON audit(organization_id,plant_id,timestamp)")
    def register_source(self,s):
        if s.source_type not in SOURCES: raise ValueError("UNSUPPORTED_SOURCE_TYPE")
        if not s.read_only: raise PermissionError("READ_ONLY_INTEGRATION_REQUIRED")
        with self.db() as c:c.execute("INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?,?,?)",(s.source_id,s.organization_id,s.plant_id,s.source_type,int(s.enabled),1,s.trust_class))
        return {"status":"REGISTERED","source_id":s.source_id,"safety":dict(SAFETY)}
    def sources(self,o,p):
        with self.db() as c:r=c.execute("SELECT * FROM sources WHERE organization_id=? AND plant_id=? ORDER BY source_id",(o,p)).fetchall()
        return {"status":"OK","sources":[dict(x) for x in r],"safety":dict(SAFETY)}
    def append(self,o,p,b):
        if not b.get("lineage"): raise ValueError("EVIDENCE_LINEAGE_REQUIRED")
        st=str(b["source_type"]).upper()
        if st not in SOURCES: raise ValueError("UNSUPPORTED_SOURCE_TYPE")
        eid=str(b.get("evidence_id") or hashlib.sha256(json.dumps([o,p,b],sort_keys=True).encode()).hexdigest()[:24])
        with self.db() as c:
            c.execute("INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?)",(eid,o,p,str(b["source_id"]),st,str(b.get("subject_type","ASSET")),str(b["subject_id"]),str(b["observed_at"]),json.dumps(b.get("payload") or {},sort_keys=True),str(b.get("quality","GOOD")).upper(),json.dumps(b["lineage"])))
            new=c.total_changes>0
        return {"status":"ACCEPTED","evidence_id":eid,"deduplicated":not new,"safety":dict(SAFETY)}
    def search(self,o,p,subject_id=None,source_type=None,limit=100):
        q="SELECT * FROM evidence WHERE organization_id=? AND plant_id=?"; a=[o,p]
        if subject_id:q+=" AND subject_id=?";a.append(subject_id)
        if source_type:q+=" AND source_type=?";a.append(source_type.upper())
        q+=" ORDER BY observed_at DESC LIMIT ?";a.append(max(1,min(int(limit),500)))
        with self.db() as c:r=c.execute(q,a).fetchall()
        out=[]
        for x in r:
            d=dict(x);d["payload"]=json.loads(d.pop("payload"));d["lineage"]=json.loads(d.pop("lineage"));out.append(d)
        return {"status":"OK","count":len(out),"evidence":out,"safety":dict(SAFETY)}
    def get(self,o,p,eid):
        r=self.search(o,p,limit=500)["evidence"]
        for x in r:
            if x["evidence_id"]==eid:return x|{"safety":dict(SAFETY)}
        raise KeyError("EVIDENCE_NOT_FOUND")
    def audit(self,o,p,action,obj,actor="SYSTEM",detail=None):
        now=datetime.now(timezone.utc).isoformat();aid=hashlib.sha256(f"{o}|{p}|{action}|{obj}|{now}".encode()).hexdigest()[:24]
        with self.db() as c:c.execute("INSERT INTO audit VALUES(?,?,?,?,?,?,?,?)",(aid,o,p,action,obj,actor,now,json.dumps(detail or {},sort_keys=True)))
        return {"audit_id":aid,"safety":dict(SAFETY)}
    def audit_list(self,o,p,limit=100):
        with self.db() as c:r=c.execute("SELECT * FROM audit WHERE organization_id=? AND plant_id=? ORDER BY timestamp DESC LIMIT ?",(o,p,max(1,min(int(limit),500)))).fetchall()
        return {"status":"OK","count":len(r),"audit":[dict(x) for x in r],"safety":dict(SAFETY)}
    def snapshot(self,o,p):
        with self.db() as c:
            s=c.execute("SELECT COUNT(*) FROM sources WHERE organization_id=? AND plant_id=?",(o,p)).fetchone()[0]
            e=c.execute("SELECT COUNT(*) FROM evidence WHERE organization_id=? AND plant_id=?",(o,p)).fetchone()[0]
            a=c.execute("SELECT COUNT(*) FROM audit WHERE organization_id=? AND plant_id=?",(o,p)).fetchone()[0]
        return {"sources":s,"evidence":e,"audit_records":a}

class V4EnterpriseIntelligence:
    def __init__(self,store=None):self.store=store or EnterpriseEvidenceStore()
    def register_source(self,o,p,b):
        r=self.store.register_source(IntegrationSource(str(b["source_id"]),str(b["source_type"]).upper(),o,p,True,True,str(b.get("trust_class","UNVERIFIED")).upper()))
        self.store.audit(o,p,"SOURCE_REGISTERED",str(b["source_id"]),str(b.get("actor","SYSTEM")));return r
    def federate(self,o,p,b):
        r=self.store.append(o,p,b);self.store.audit(o,p,"EVIDENCE_FEDERATED",r["evidence_id"],str(b.get("actor","SYSTEM")));return r
    def context(self,o,p,subject):
        r=self.store.search(o,p,subject_id=subject,limit=500);types={}
        for x in r["evidence"]:types[x["source_type"]]=types.get(x["source_type"],0)+1
        return {"status":"OK","subject_id":subject,"evidence_count":r["count"],"sources":types,"corroboration":len(types)>=2,"causal_claimed":False,"safety":dict(SAFETY)}
    def benchmark(self,o,plants):
        for x in plants:
            if str(x.get("organization_id"))!=str(o):raise PermissionError("TENANT_BOUNDARY_VIOLATION")
        return {"status":"OK","organization_id":o,"plants":plants,"benchmarking_method":"DESCRIPTIVE_ONLY","causal_claimed":False,"cross_plant_fallback":False,"safety":dict(SAFETY)}
    def summary(self,o,p):
        return {"product":"ANVIQO","version":"V4.0 ENTERPRISE INDUSTRIAL INTELLIGENCE","scope":{"organization_id":o,"plant_id":p},"milestones":{"v3_5_evidence_federation":True,"v3_6_enterprise_connectors":True,"v3_7_audit_lineage":True,"v3_8_fleet_intelligence":True,"v3_9_management_intelligence":True,"v4_0_multi_plant_boundary":True,"ha_dr_contract":True},"integration_boundary":{"read_only":True,"supported_sources":sorted(SOURCES)},"store":self.store.snapshot(o,p),"safety":dict(SAFETY)}
    def hadr(self,o,p):return {"status":"CONTRACT_DEFINED","organization_id":o,"plant_id":p,"backup_required":True,"restore_test_required":True,"rpo":"EXTERNAL_POLICY_REQUIRED","rto":"EXTERNAL_POLICY_REQUIRED","failover_automation_claimed":False,"safety":dict(SAFETY)}

enterprise=V4EnterpriseIntelligence()

def register(app):
    from flask import jsonify,request,session
    def req():
        o=session.get("organization_id","");p=session.get("plant_id","")
        return (str(o),str(p)) if o and p else None
    def guard():
        s=req();return s if s else (jsonify({"status":"TENANT_UNAVAILABLE","safety":dict(SAFETY)}),409)
    @app.get("/api/v4/enterprise/summary")
    def v4_summary():
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        return jsonify(enterprise.summary(*s))
    @app.get("/api/v4/integration/sources")
    def v4_sources():
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        return jsonify(enterprise.store.sources(*s))
    @app.post("/api/v4/integration/sources")
    def v4_source():
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        try:return jsonify(enterprise.register_source(*s,request.get_json(silent=True) or {}))
        except Exception as x:return jsonify({"status":"BAD_REQUEST","message":str(x),"safety":dict(SAFETY)}),400
    @app.post("/api/v4/evidence/federate")
    def v4_fed():
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        try:return jsonify(enterprise.federate(*s,request.get_json(silent=True) or {}))
        except PermissionError as x:return jsonify({"status":"FORBIDDEN","message":str(x),"safety":dict(SAFETY)}),403
        except Exception as x:return jsonify({"status":"BAD_REQUEST","message":str(x),"safety":dict(SAFETY)}),400
    @app.get("/api/v4/evidence/<eid>")
    def v4_ev(eid):
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        try:return jsonify(enterprise.store.get(*s,eid))
        except KeyError:return jsonify({"status":"NOT_FOUND","safety":dict(SAFETY)}),404
    @app.get("/api/v4/evidence/search")
    def v4_search():
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        return jsonify(enterprise.store.search(*s,request.args.get("subject_id"),request.args.get("source_type"),request.args.get("limit",100)))
    @app.get("/api/v4/evidence/context/<subject>")
    def v4_context(subject):
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        return jsonify(enterprise.context(*s,subject))
    @app.get("/api/v4/audit")
    def v4_audit():
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        return jsonify(enterprise.store.audit_list(*s,request.args.get("limit",100)))
    @app.post("/api/v4/fleet/benchmark")
    def v4_benchmark():
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        try:return jsonify(enterprise.benchmark(s[0],(request.get_json(silent=True) or {}).get("plants",[])))
        except PermissionError as x:return jsonify({"status":"FORBIDDEN","message":str(x),"safety":dict(SAFETY)}),403
    @app.get("/api/v4/ha-dr")
    def v4_hadr():
        s=guard()
        if isinstance(s,tuple) and len(s)==2 and not isinstance(s[0],str):return s
        return jsonify(enterprise.hadr(*s))
    @app.get("/api/v4/safety")
    def v4_safety():return jsonify({"status":"SAFE READ-ONLY ENTERPRISE MODE","safety":dict(SAFETY)})
