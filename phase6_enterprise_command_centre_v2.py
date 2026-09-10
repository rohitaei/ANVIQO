"""ANVIQO Phase 6 Enterprise Command Centre V2.

Presentation/context adapter only. Reuses Phase 6 organization/plant context
and the existing Phase 5 HOD intelligence endpoint. No new reasoning engine.
"""
from __future__ import annotations

from flask import jsonify, render_template_string

from phase6_enterprise_runtime import app, _require_auth, _actor, _connect, _placeholder

ENTERPRISE_V2_GOVERNANCE = {
    "read_only_intelligence": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def _plants(actor):
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT plant_id,name,slug,status,created_at FROM anviqo_plants WHERE organization_id={p} ORDER BY name", (actor["organization_id"],))
        return [dict(r) for r in cur.fetchall()]


@app.route("/api/enterprise/command-centre")
def enterprise_command_centre_api():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    return jsonify({
        "status": "OK",
        "organization": {"organization_id": actor["organization_id"], "username": actor["username"], "role": actor["role"]},
        "active_plant_id": actor["plant_id"],
        "plants": _plants(actor),
        "intelligence_route": "/api/hod-management",
        "governance": dict(ENTERPRISE_V2_GOVERNANCE),
    })


ENTERPRISE_HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>ANVIQO | Enterprise Command Centre</title>
<style>body{margin:0;background:#07111f;color:#eaf2f8;font-family:Arial,sans-serif}.wrap{max-width:1280px;margin:auto;padding:22px}.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #20354d;padding-bottom:15px}.brand{font-size:25px;font-weight:700;color:#37d6e8}.muted{color:#8299af;font-size:12px}.layout{display:grid;grid-template-columns:280px 1fr;gap:14px;margin-top:16px}.panel,.plant{background:#0e1d30;border:1px solid #213952;border-radius:10px;padding:15px}.plant{margin-bottom:8px}.plant.active{border-color:#37d6e8}.hero{font-size:22px;font-weight:700}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}.card{background:#0e1d30;border:1px solid #213952;border-radius:10px;padding:15px}.value{font-size:19px;font-weight:700;margin-top:7px}.row{padding:10px 0;border-bottom:1px solid #172c43}.row:last-child{border:0}.safety{margin-top:14px;padding:11px;border:1px solid #1d5a42;border-radius:8px;color:#28d17c;font-size:10px;font-weight:700}@media(max-width:850px){.layout{grid-template-columns:1fr}.cards{grid-template-columns:repeat(2,1fr)}}@media(max-width:520px){.cards{grid-template-columns:1fr}}</style></head><body><div class="wrap"><div class="top"><div><div class="brand">ANVIQO</div><div class="muted">ENTERPRISE COMMAND CENTRE · THINK • PREDICT • PROTECT</div></div><div id="org" class="muted">Loading…</div></div><div class="layout"><div><div class="panel"><div class="muted">ORGANIZATION / PLANTS</div><div id="plants" style="margin-top:12px">—</div></div></div><div><div class="panel"><div class="hero" id="plant">Active Plant</div><div class="muted">Enterprise context → existing ANVIQO intelligence</div></div><div class="cards"><div class="card"><div class="muted">MANAGEMENT</div><div class="value" id="ms">—</div></div><div class="card"><div class="muted">SITUATION</div><div class="value" id="sit">—</div></div><div class="card"><div class="muted">PLANT HEALTH</div><div class="value" id="health">—</div></div><div class="card"><div class="muted">HUMAN REVIEW</div><div class="value" id="reviews">—</div></div></div><div class="panel" style="margin-top:12px"><div class="muted">MANAGEMENT INTELLIGENCE</div><div id="message" style="margin-top:10px">—</div><div id="priority"></div></div><div class="safety">READ-ONLY · PLC WRITE BLOCKED · SCADA CONTROL BLOCKED · AUTOMATIC AUTHORIZATION DISABLED · AUTOMATIC EXECUTION DISABLED · HUMAN DECISION REQUIRED</div></div></div></div><script>function esc(v){return String(v??'—').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}async function load(){try{const r=await fetch('/api/enterprise/command-centre');const d=await r.json();if(d.status!=='OK')throw Error();const ps=d.plants||[];document.getElementById('org').textContent=esc(d.organization.username)+' · '+esc(d.organization.role);document.getElementById('plants').innerHTML=ps.length?ps.map(p=>'<div class="plant '+(p.plant_id===d.active_plant_id?'active':'')+'"><b>'+esc(p.name)+'</b><br><span class="muted">'+esc(p.slug)+' · '+esc(p.status)+'</span></div>').join(''):'No plants available';document.getElementById('plant').textContent=(ps.find(p=>p.plant_id===d.active_plant_id)||{}).name||'Active Plant';const h=await (await fetch('/api/hod-management')).json();document.getElementById('ms').textContent=esc(h.management_state);document.getElementById('sit').textContent=esc(h.plant_situation);const ph=h.plant_health||{};document.getElementById('health').textContent=esc(ph.score)+(ph.status?' · '+esc(ph.status):'');const p=h.top_priorities||[];document.getElementById('reviews').textContent=p.length;document.getElementById('message').textContent=esc(h.management_message);document.getElementById('priority').innerHTML=p.map(x=>'<div class="row"><b>'+esc(x.equipment)+'</b> · priority '+esc(x.priority)+'/100<br><span class="muted">'+esc(x.reason)+' · HUMAN REVIEW</span></div>').join('')}catch(e){document.getElementById('org').textContent='Enterprise context unavailable'}}load();setInterval(load,30000)</script></body></html>"""


@app.route("/enterprise")
def enterprise_command_centre_view():
    return render_template_string(ENTERPRISE_HTML)
