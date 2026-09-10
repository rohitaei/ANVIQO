"""ANVIQO Phase 5 Command Centre integration.

Thin presentation/API adapter over existing V5 Executive/HOD and Phase 4
contracts. It never creates plant facts and never executes actions.
"""
from __future__ import annotations

from flask import jsonify, render_template_string, request

from anviqo_spare_query_guard import app
from phase5_human_management_intelligence import (
    SAFETY_BOUNDARY,
    build_management_brief,
    create_human_action_queue,
    record_human_decision,
)
from phase5_live_evidence_adapter import build_live_management_evidence


@app.route("/api/hod-management", methods=["GET", "POST"])
def hod_management_api():
    """Build the Phase 5 HOD brief from existing evidence contracts."""
    if request.method == "GET":
        try:
            payload = build_live_management_evidence()
        except Exception as exc:
            return jsonify({
                "status": "INSUFFICIENT_EVIDENCE",
                "message": "Existing plant evidence could not be assembled.",
                "error_type": type(exc).__name__,
                "safety_boundary": dict(SAFETY_BOUNDARY),
                "evidence_available": False,
            })
    else:
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return jsonify({"status": "ERROR", "message": "JSON object required", "safety_boundary": dict(SAFETY_BOUNDARY)}), 400

    result = build_management_brief(
        executive=payload.get("executive", {}),
        phase4=payload.get("phase4", {}),
        shift=payload.get("shift", {}),
    )
    result["source"] = "ANVIQO Phase 5 Management Contract"
    result["evidence_context"] = payload.get("evidence_context", {})
    result["areas"] = payload.get("areas", [])
    result["action_queue"] = create_human_action_queue(result, payload.get("actions"))
    return jsonify(result)


@app.route("/api/hod-management/decision", methods=["POST"])
def hod_management_decision_api():
    """Record a human decision only; no approval triggers execution."""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"status": "ERROR", "message": "JSON object required", "executed": False}), 400
    action = payload.get("action")
    decision = payload.get("decision")
    if not isinstance(action, dict) or not decision:
        return jsonify({"status": "BAD_REQUEST", "message": "action and decision are required", "executed": False}), 400
    result = record_human_decision(action, decision, reviewer=payload.get("reviewer"), note=payload.get("note", ""))
    if result.get("status") == "ERROR":
        return jsonify(result), 400
    result["safety_boundary"] = dict(SAFETY_BOUNDARY)
    return jsonify(result)


MANAGEMENT_HTML = """<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>ANVIQO | HOD Management</title>
<style>body{margin:0;background:#07111f;color:#eaf2f8;font-family:Arial,sans-serif}.wrap{max-width:1200px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #20354d;padding-bottom:16px}.brand{font-size:24px;font-weight:700;color:#37d6e8}.muted{color:#8299af;font-size:12px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}.card,.panel{background:#0e1d30;border:1px solid #213952;border-radius:10px;padding:16px}.value{font-size:20px;font-weight:700;margin-top:8px}.panel{margin-top:14px}.title{color:#37d6e8;font-weight:700;font-size:12px;margin-bottom:12px}.row{padding:11px 0;border-bottom:1px solid #172c43}.row:last-child{border:0}.priority{float:right;font-weight:700}.badge{display:inline-block;padding:4px 7px;border:1px solid #31516d;border-radius:6px;font-size:10px;margin:2px}.safety{margin-top:16px;padding:12px;border:1px solid #1d5a42;border-radius:8px;color:#28d17c;font-size:11px;font-weight:700}@media(max-width:800px){.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:520px){.grid{grid-template-columns:1fr}}</style></head><body><div class="wrap"><div class="top"><div><div class="brand">ANVIQO</div><div class="muted">HUMAN & MANAGEMENT INTELLIGENCE</div></div><div id="state" class="muted">Loading verified evidence…</div></div><div class="grid"><div class="card"><div class="muted">MANAGEMENT STATE</div><div id="mstate" class="value">—</div></div><div class="card"><div class="muted">PLANT SITUATION</div><div id="situation" class="value">—</div></div><div class="card"><div class="muted">PLANT HEALTH</div><div id="health" class="value">—</div></div><div class="card"><div class="muted">REVIEW ITEMS</div><div id="count" class="value">0</div></div></div><div class="panel"><div class="title">MANAGEMENT MESSAGE</div><div id="message">—</div></div><div class="panel"><div class="title">TOP PRIORITIES / HUMAN REVIEW</div><div id="priorities">—</div></div><div class="panel"><div class="title">WHAT CHANGED</div><div id="changes">—</div></div><div class="panel"><div class="title">AREA HEALTH</div><div id="areas">—</div></div><div class="panel"><div class="title">SHIFT / CURRENT EVIDENCE</div><div id="shift">—</div></div><div class="safety">READ-ONLY · PLC WRITE BLOCKED · SCADA CONTROL BLOCKED · AUTOMATIC AUTHORIZATION DISABLED · AUTOMATIC EXECUTION DISABLED · HUMAN DECISION REQUIRED</div></div><script>
function text(v){return v===null||v===undefined?'—':String(v)}
function esc(v){return text(v).replace(/[&<>\"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]})}
async function load(){try{const r=await fetch('/api/hod-management');const d=await r.json();document.getElementById('mstate').textContent=text(d.management_state);document.getElementById('situation').textContent=text(d.plant_situation);const h=d.plant_health||{};document.getElementById('health').textContent=text(h.score)+(h.status?' · '+text(h.status):'');const p=d.top_priorities||[];document.getElementById('count').textContent=p.length;document.getElementById('message').textContent=text(d.management_message);document.getElementById('priorities').innerHTML=p.length?p.map(x=>'<div class="row"><b>'+esc(x.equipment)+'</b><span class="priority">'+esc(x.priority)+'/100</span><br><span class="muted">'+esc(x.status)+' · '+esc(x.reason)+'</span><br><span class="muted">Human action: REVIEW</span></div>').join(''):'No prioritized equipment risk supplied by the existing intelligence layer.';const c=d.what_changed||[];document.getElementById('changes').innerHTML=c.length?c.map(x=>'<div class="row">✓ '+esc(x)+'</div>').join(''):'No verified change indicators supplied.';const a=d.areas||[];document.getElementById('areas').innerHTML=a.length?a.map(x=>'<span class="badge">'+esc(x.area)+' · '+esc(x.status)+' · '+esc(x.health_score)+'/100</span>').join(''):'No area evidence supplied.';const s=d.shift_summary||{};document.getElementById('shift').textContent=JSON.stringify(s);const sim=d.evidence_context&&String(d.evidence_context.mode||'').toUpperCase()==='SIMULATION';document.getElementById('state').textContent=sim?'DEMO / SIMULATION EVIDENCE':'Evidence-backed view'}catch(e){document.getElementById('state').textContent='Management view unavailable'}}load();setInterval(load,30000)
</script></body></html>"""


@app.route("/management")
def management_view():
    return render_template_string(MANAGEMENT_HTML)
