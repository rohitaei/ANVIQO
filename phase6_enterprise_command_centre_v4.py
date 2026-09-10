"""ANVIQO Phase 6 Enterprise Command Centre V4.

Real tenant-scoped plant-context switching. This module changes only the
authenticated session context; it never changes PLC/SCADA state and never
creates intelligence for a plant whose evidence is not actually available.
"""
from __future__ import annotations

from flask import jsonify, request, render_template_string, session

from phase6_enterprise_runtime import app, _actor, _connect, _placeholder, _require_auth, _admin
from anvi_tenant_store import authorize, create_membership, get_membership, record_audit

ENTERPRISE_V4_GOVERNANCE = {
    "read_only_intelligence": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def _plant(actor, plant_id):
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT plant_id,organization_id,name,slug,status,created_at FROM anviqo_plants WHERE organization_id={p} AND plant_id={p}", (actor["organization_id"], plant_id))
        row = cur.fetchone()
    return dict(row) if row else None


def _ensure_admin_membership(actor, plant_id):
    if _admin(actor) and get_membership(actor["user_id"], actor["organization_id"], plant_id) is None:
        create_membership(actor["user_id"], actor["organization_id"], plant_id, "ADMIN")


def _can_read_plant(actor, plant_id):
    if _admin(actor):
        return True
    selected_actor = dict(actor)
    selected_actor["plant_id"] = plant_id
    return authorize(selected_actor, "plant:read", actor["organization_id"], plant_id)


@app.route("/api/enterprise/select-plant", methods=["POST"])
def enterprise_select_plant():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    payload = request.get_json(silent=True) or {}
    plant_id = str(payload.get("plant_id", "")).strip()
    if not plant_id:
        return jsonify({"status": "BAD_REQUEST", "message": "plant_id is required", "switched": False, "governance": dict(ENTERPRISE_V4_GOVERNANCE)}), 400
    plant = _plant(actor, plant_id)
    if plant is None:
        return jsonify({"status": "FORBIDDEN", "message": "Plant is outside the active organization", "switched": False, "governance": dict(ENTERPRISE_V4_GOVERNANCE)}), 403
    if not _can_read_plant(actor, plant_id):
        return jsonify({"status": "FORBIDDEN", "message": "plant:read permission is required for the selected plant", "switched": False, "governance": dict(ENTERPRISE_V4_GOVERNANCE)}), 403
    previous_plant_id = actor["plant_id"]
    _ensure_admin_membership(actor, plant_id)
    session["plant_id"] = plant_id
    session.modified = True
    try:
        audit_actor = dict(actor)
        audit_actor["plant_id"] = plant_id
        record_audit(audit_actor, "SELECT_PLANT_CONTEXT", "plant", plant_id, {"previous_plant_id": previous_plant_id})
    except Exception:
        pass
    return jsonify({"status": "SWITCHED", "switched": True, "previous_plant_id": previous_plant_id, "active_plant_id": plant_id, "plant": plant, "evidence_scope": {"plant_id": plant_id, "policy": "existing_evidence_only", "status": "CONTEXT_SELECTED", "note": "Existing intelligence must be evaluated in this selected plant context; no evidence is fabricated by the context switch."}, "governance": dict(ENTERPRISE_V4_GOVERNANCE)})


@app.route("/api/enterprise/active-context")
def enterprise_active_context():
    denied = _require_auth()
    if denied:
        return denied
    actor = _actor()
    plant = _plant(actor, actor["plant_id"]) if actor["plant_id"] else None
    return jsonify({"status": "OK", "organization_id": actor["organization_id"], "active_plant_id": actor["plant_id"], "plant": plant, "evidence_policy": "existing_evidence_only", "governance": dict(ENTERPRISE_V4_GOVERNANCE)})


def _v4_plants(actor):
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT plant_id,name,slug,status,created_at FROM anviqo_plants WHERE organization_id={p} ORDER BY name", (actor["organization_id"],))
        return [dict(r) for r in cur.fetchall()]


ENTERPRISE_V4_HTML = """<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>ANVIQO | Enterprise Command Centre</title><style>body{margin:0;background:#07111f;color:#eaf2f8;font-family:Arial,sans-serif}.wrap{max-width:1180px;margin:auto;padding:22px}.top{display:flex;justify-content:space-between;border-bottom:1px solid #20354d;padding-bottom:14px}.brand{font-size:25px;font-weight:700;color:#37d6e8}.muted{color:#8299af;font-size:12px}.grid{display:grid;grid-template-columns:290px 1fr;gap:14px;margin-top:16px}.panel{background:#0e1d30;border:1px solid #213952;border-radius:10px;padding:15px}.plant{padding:12px;margin-top:8px;border:1px solid #213952;border-radius:8px;cursor:pointer}.plant.active{border-color:#37d6e8}.title{font-size:22px;font-weight:700}.badge{display:inline-block;margin-top:12px;padding:7px 9px;border-radius:6px;border:1px solid #1d5a42;color:#28d17c;font-size:10px;font-weight:700}.note{margin-top:12px;line-height:1.55}.safety{margin-top:14px;padding:11px;border:1px solid #1d5a42;border-radius:8px;color:#28d17c;font-size:10px;font-weight:700}@media(max-width:760px){.grid{grid-template-columns:1fr}}</style></head><body><div class='wrap'><div class='top'><div><div class='brand'>ANVIQO</div><div class='muted'>ENTERPRISE COMMAND CENTRE · THINK • PREDICT • PROTECT</div></div><div id='role' class='muted'>Loading…</div></div><div class='grid'><div class='panel'><div class='muted'>ORGANIZATION / PLANTS</div><div id='plants'>—</div></div><div><div class='panel'><div id='plant' class='title'>Active Plant</div><div id='slug' class='muted'></div><div id='scope' class='badge'>—</div><div class='note'><b>Plant context is switched for this session.</b><br>ANVIQO will only show intelligence backed by evidence belonging to the selected plant. No health, risk, production, energy, reliability, event, or maintenance fact is fabricated when plant-scoped evidence is unavailable.</div></div><div class='safety'>READ-ONLY · PLC WRITE BLOCKED · SCADA CONTROL BLOCKED · AUTOMATIC AUTHORIZATION DISABLED · AUTOMATIC EXECUTION DISABLED · HUMAN DECISION REQUIRED</div></div></div></div><script>const esc=v=>String(v??'—').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));async function load(){const r=await fetch('/api/enterprise/context');const d=await r.json();if(d.status!=='OK')return;document.getElementById('role').textContent=esc(d.role)+' · '+esc(d.organization?.name);const ps=d.plants||[];document.getElementById('plants').innerHTML=ps.map(p=>'<div class="plant '+(p.plant_id===d.active_plant_id?'active':'')+'" onclick="selectPlant(\''+encodeURIComponent(p.plant_id)+'\')"><b>'+esc(p.name)+'</b><br><span class="muted">'+esc(p.slug)+' · '+esc(p.status)+'</span></div>').join('');const p=ps.find(x=>x.plant_id===d.active_plant_id);document.getElementById('plant').textContent=p?.name||'Active Plant';document.getElementById('slug').textContent=p?.slug||'';document.getElementById('scope').textContent='ACTIVE CONTEXT · EXISTING EVIDENCE ONLY'}async function selectPlant(id){const r=await fetch('/api/enterprise/select-plant',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plant_id:decodeURIComponent(id)})});const d=await r.json();if(d.switched){await load()}else{alert(d.message||'Plant switch denied')}}load();setInterval(load,30000)</script></body></html>"""


def enterprise_command_centre_v4_view():
    denied = _require_auth()
    if denied:
        return denied
    return render_template_string(ENTERPRISE_V4_HTML)


# V2 already registered /enterprise. Replace only its presentation function;
# the route and all existing V2 intelligence APIs remain intact.
app.view_functions["enterprise_command_centre_view"] = enterprise_command_centre_v4_view
