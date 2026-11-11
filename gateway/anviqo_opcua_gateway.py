"""Read-only OPC UA edge gateway. Run on an approved OT/DMZ industrial PC."""
import asyncio, json, os
from datetime import datetime, timezone
import requests
from asyncua import Client

def load_tags(path):
    with open(path, encoding="utf-8") as f: config=json.load(f)
    if not config.get("tags"): raise RuntimeError("No tag map configured")
    for item in config["tags"]:
        if not item.get("tag") or not item.get("node_id"): raise RuntimeError("tag and node_id required")
    return config

async def run():
    endpoint=os.environ["ANVIQO_OPCUA_ENDPOINT"]
    url=os.environ["ANVIQO_INGEST_URL"].rstrip("/")+"/api/gateway/v1/telemetry"
    token=os.environ["ANVIQO_PLC_INGEST_TOKEN"]
    gateway=os.getenv("ANVIQO_GATEWAY_ID","anviqo-ot-gateway-01")
    config=load_tags(os.getenv("ANVIQO_TAG_MAP","tags.json"))
    interval=max(1.0,float(os.getenv("ANVIQO_POLL_SECONDS","2")))
    client=Client(url=endpoint,timeout=8)
    username=os.getenv("ANVIQO_OPCUA_USERNAME")
    if username:
        client.set_user(username); client.set_password(os.getenv("ANVIQO_OPCUA_PASSWORD",""))
    security=os.getenv("ANVIQO_OPCUA_SECURITY_STRING","")
    if security: await client.set_security_string(security)
    with requests.Session() as http:
        http.headers.update({"Authorization":"Bearer "+token,"Content-Type":"application/json"})
        async with client:
            nodes=[(x,client.get_node(x["node_id"])) for x in config["tags"]]
            while True:
                batch=[]
                for item,node in nodes:
                    try:
                        dv=await node.read_data_value()
                        status=str(dv.StatusCode).upper()
                        quality="GOOD" if "GOOD" in status else ("UNCERTAIN" if "UNCERTAIN" in status else "BAD")
                        value=dv.Value.Value
                        if isinstance(value,bool) or not isinstance(value,(int,float)): continue
                        ts=dv.SourceTimestamp or datetime.now(timezone.utc)
                        if ts.tzinfo is None: ts=ts.replace(tzinfo=timezone.utc)
                        batch.append({"tag":item["tag"],"value":value,"unit":item.get("unit",""),
                            "quality":quality,"timestamp":ts.astimezone(timezone.utc).isoformat()})
                    except Exception: continue
                if batch:
                    response=http.post(url,json={"gateway_id":gateway,"points":batch},timeout=10)
                    response.raise_for_status()
                await asyncio.sleep(interval)

if __name__=="__main__": asyncio.run(run())
