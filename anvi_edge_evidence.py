"""Tenant-scoped real-time evidence adapter for ANVIQO edge observations."""
from __future__ import annotations
import json
from typing import Any, List, Optional
from anvi_tenant_store import _connect, _placeholder, init_schema

def _rows(plant_id: str, organization_id: str, tag: Optional[str] = None, limit: int = 250) -> List[dict]:
    if not plant_id or not organization_id: return []
    init_schema(); p=_placeholder()
    sql=("SELECT observation_id,organization_id,plant_id,gateway_id,tag,value,timestamp,quality,source,protocol,received_at "
         "FROM anviqo_edge_observations WHERE organization_id="+p+" AND plant_id="+p)
    params=[organization_id,plant_id]
    if tag:
        sql+=" AND UPPER(REPLACE(REPLACE(tag,'_','-'),' ', '-'))=UPPER(REPLACE(REPLACE("+p+",'_','-'),' ', '-'))"
        params.append(str(tag))
    sql+=" ORDER BY timestamp DESC LIMIT "+str(max(1,min(int(limit),1000)))
    try:
        with _connect() as conn:
            cur=conn.cursor(); cur.execute(sql,tuple(params)); rows=cur.fetchall()
    except Exception: return []
    out=[]
    for r in rows:
        value=r[5]
        if isinstance(value,str):
            try: value=json.loads(value)
            except Exception: pass
        out.append({"observation_id":r[0],"organization_id":r[1],"plant_id":r[2],"gateway_id":r[3],
                    "tag":r[4],"value":value,"timestamp":r[6],"quality":r[7],"source":r[8],
                    "protocol":r[9],"received_at":r[10]})
    return out

def latest(plant_id: str, organization_id: str, tag: Optional[str] = None):
    rows=_rows(plant_id,organization_id,tag,100); return rows[0] if rows else None

def state(plant_id: str, organization_id: str, tag: Optional[str] = None, limit: int = 250):
    rows=_rows(plant_id,organization_id,tag,limit)
    return {"status":"AVAILABLE" if rows else "NO_EVIDENCE","scope":"SELECTED_PLANT_ONLY",
            "plant_id":plant_id,"organization_id":organization_id,"tag":tag,
            "latest":rows[0] if rows else None,"observations":rows,"observation_count":len(rows),
            "safety":{"read_only":True,"plc_write":False,"scada_control":False,
                      "human_decision_required":True,"automatic_authorization":False,
                      "automatic_execution":False}}
