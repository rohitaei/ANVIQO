"""ANVIQO Command Centre Failure Prediction Demo dashboard runtime injection.

Keeps the existing dashboard HTML intact while adding the explicitly simulated
Failure Prediction Demo panel at runtime. This is UI-only decision support.
"""
from __future__ import annotations

from flask import request

from anviqo_spare_query_guard import app

VERSION = "ANVIQO-FP-DEMO-DASHBOARD-V1.1"

SAFETY = {
    "mode": "DEMO_SIMULATION_ONLY",
    "production_history_write": False,
    "plc_write": False,
    "scada_control": False,
    "automatic_execution": False,
    "human_decision_required": True,
}

PANEL_HTML = r'''
<style id="anviqo-fp-demo-style">
#anviqoFpDemo{margin-top:14px}
.fp-demo-banner{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap;padding:10px 12px;border:1px solid #6b541c;background:#251f10;border-radius:9px;margin-bottom:12px}
.fp-demo-banner b{color:#ffc45c;font-size:9px;letter-spacing:1.2px}
.fp-demo-banner span{font-size:8px;color:#d7b86b}
.fp-demo-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:12px}
.fp-demo-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.fp-demo-metric{padding:11px;border:1px solid #193b49;border-radius:8px;background:#07151d}
.fp-demo-metric label{display:block;font-size:7px;color:#668592;letter-spacing:1px}
.fp-demo-metric strong{display:block;font-size:18px;margin-top:5px}
.fp-demo-chart{height:180px;position:relative;margin-top:12px;border:1px solid #193b49;border-radius:8px;background:#06131b;overflow:hidden}
.fp-demo-chart svg{width:100%;height:100%;display:block}
.fp-demo-legend{font-size:8px;color:#7895a3;margin-top:6px}
@media(max-width:900px){.fp-demo-grid{grid-template-columns:1fr}.fp-demo-metrics{grid-template-columns:repeat(2,1fr)}}
</style>
<div id="anviqoFpDemo" class="card">
 <div class="card-head"><b>FAILURE PREDICTION DEMO</b><span>PT-303 • SIMULATION</span></div>
 <div class="card-body">
  <div class="fp-demo-banner"><b>⚠ DEMO / SYNTHETIC DATA — NOT PLANT TELEMETRY</b><span>Decision support only • no production history write</span></div>
  <div id="fpDemoStatus" class="empty">Loading demo prediction...</div>
  <div id="fpDemoBody" style="display:none">
   <div class="fp-demo-grid">
    <div>
     <div class="fp-demo-metrics">
      <div class="fp-demo-metric"><label>OBSERVATIONS</label><strong id="fpObs">—</strong></div>
      <div class="fp-demo-metric"><label>FIRST</label><strong id="fpFirst">—</strong></div>
      <div class="fp-demo-metric"><label>LAST</label><strong id="fpLast">—</strong></div>
      <div class="fp-demo-metric"><label>DELTA</label><strong id="fpDelta" class="amber">—</strong></div>
     </div>
     <div class="card" style="margin-top:10px">
      <div class="card-head"><b>DOCUMENTED DEMO TREND</b><span id="fpDirection" class="badge amber">—</span></div>
      <div class="card-body">
       <div id="fpChart" class="fp-demo-chart"></div>
       <div id="fpLegend" class="fp-demo-legend"></div>
      </div>
     </div>
    </div>
    <div class="card">
     <div class="card-head"><b>PREDICTION</b><span>V1.0 DEMO</span></div>
     <div class="card-body">
      <div id="fpPrediction" style="font-size:11px;line-height:1.7"></div>
      <div class="row"><span>Failure probability</span><b class="muted">Not calculated</b></div>
      <div class="row"><span>Failure date</span><b class="muted">Not calculated</b></div>
      <div class="row"><span>Production history write</span><b class="red">BLOCKED</b></div>
      <div class="row"><span>PLC / SCADA control</span><b class="red">BLOCKED</b></div>
      <div class="row"><span>Human decision</span><b class="green">REQUIRED</b></div>
     </div>
    </div>
   </div>
  </div>
 </div>
</div>
'''

SCRIPT = r'''
<script id="anviqo-fp-demo-script">
(function(){
  function draw(points){
    var box=document.getElementById('fpChart'); if(!box||!points||points.length<2)return;
    var w=700,h=180,p=18, vals=points.map(function(x){return Number(x.value)}).filter(Number.isFinite);
    if(vals.length<2)return;
    var min=Math.min.apply(Math,vals),max=Math.max.apply(Math,vals); if(max===min){max=min+1}
    var xy=points.map(function(x,i){var xx=p+(i*(w-2*p)/(points.length-1));var yy=h-p-((Number(x.value)-min)*(h-2*p)/(max-min));return [xx,yy]});
    var path=xy.map(function(a,i){return (i?'L':'M')+a[0].toFixed(1)+' '+a[1].toFixed(1)}).join(' ');
    var circles=xy.map(function(a){return '<circle cx="'+a[0].toFixed(1)+'" cy="'+a[1].toFixed(1)+'" r="3" fill="currentColor"/>'}).join('');
    box.innerHTML='<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" aria-label="PT-303 simulated trend"><line x1="18" y1="162" x2="682" y2="162" stroke="#193b49"/><line x1="18" y1="18" x2="18" y2="162" stroke="#193b49"/><path d="'+path+'" fill="none" stroke="#31d8f5" stroke-width="3"/>'+circles+'</svg>';
  }
  async function load(){
    var root=document.getElementById('anviqoFpDemo'); if(!root)return;
    var status=document.getElementById('fpDemoStatus'),body=document.getElementById('fpDemoBody');
    try{
      var r=await fetch('/api/failure_prediction/demo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag:'PT-303'})});
      var d=await r.json(); if(!r.ok)throw Error(d.message||'Demo API error');
      if(d.simulation!==true||d.source!=='SIMULATION')throw Error('Demo safety contract rejected the response');
      document.getElementById('fpObs').textContent=d.observations??'—';
      document.getElementById('fpFirst').textContent=(d.first_value??'—')+' '+(d.unit||'');
      document.getElementById('fpLast').textContent=(d.last_value??'—')+' '+(d.unit||'');
      document.getElementById('fpDelta').textContent=(d.delta>0?'+':'')+(d.delta??'—')+' '+(d.unit||'');
      document.getElementById('fpDirection').textContent=d.direction||'—';
      document.getElementById('fpPrediction').textContent=d.prediction||'Prediction unavailable.';
      document.getElementById('fpLegend').textContent='Synthetic PT-303 telemetry • '+(d.observations||0)+' observations • '+(d.provenance||'ANVIQO DEMO');
      draw(d.trend_points||[]);
      status.style.display='none';body.style.display='block';
    }catch(e){status.textContent='Demo prediction unavailable: '+e.message;}
  }
  function start(){
    var page=document.getElementById('page-prediction'); if(!page||document.getElementById('anviqoFpDemo'))return;
    page.insertAdjacentHTML('beforeend',window.__ANVIQO_FP_DEMO_PANEL_HTML__||'');
    load();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
</script>
'''

BOOTSTRAP = '<script>window.__ANVIQO_FP_DEMO_PANEL_HTML__=' + repr(PANEL_HTML) + ';</script>'


def inject_prediction_demo_dashboard(html: str) -> str:
    """Inject the demo panel into the existing Predictive Intelligence page."""
    text = str(html or '')
    if 'id="page-prediction"' not in text:
        return text
    if 'id="anviqoFpDemo"' in text:
        return text
    lower = text.lower()
    marker = '</body>'
    idx = lower.find(marker)
    if idx < 0:
        return text
    return text[:idx] + BOOTSTRAP + SCRIPT + '\n' + text[idx:]


@app.after_request
def inject_failure_prediction_demo_dashboard(response):
    if request.method != 'GET' or response.status_code != 200:
        return response
    content_type = str(response.headers.get('Content-Type', '')).lower()
    if 'text/html' not in content_type:
        return response
    try:
        html = response.get_data(as_text=True)
        updated = inject_prediction_demo_dashboard(html)
        if updated != html:
            response.set_data(updated)
            response.headers.pop('Content-Length', None)
    except Exception:
        pass
    return response
