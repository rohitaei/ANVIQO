"""ANVIQO V2 Command Centre UI runtime injection.
Adds a read-only V2 evidence panel to the existing dashboard at response time.
The frozen dashboard source and V5 intelligence modules are not modified.
"""
from flask import request
from phase6_enterprise_runtime import app

MARKER = "ANVI_V2_RUNTIME_PANEL"

PANEL = r'''<div id="ANVI_V2_RUNTIME_PANEL" style="margin:14px 0;padding:14px;border:1px solid #193b49;border-radius:13px;background:#09151d;color:#e8f6fa;font-family:Inter,system-ui,sans-serif">
<div style="font-size:9px;color:#31d8f5;letter-spacing:1.7px;font-weight:800">V2 REAL-TIME INDUSTRIAL INTELLIGENCE</div>
<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin-top:10px">
<div style="padding:11px;border:1px solid #193b49;border-radius:9px;background:#06151f"><b style="font-size:10px">WHAT CHANGED</b><div id="anviV2Changed" style="margin-top:7px;font-size:9px;color:#7895a3">Loading scoped evidence…</div></div>
<div style="padding:11px;border:1px solid #193b49;border-radius:9px;background:#06151f"><b style="font-size:10px">EVENT CORRELATION</b><div id="anviV2Correlation" style="margin-top:7px;font-size:9px;color:#7895a3;cursor:pointer">Tap to inspect equipment event sequence.</div></div>
<div style="padding:11px;border:1px solid #193b49;border-radius:9px;background:#06151f"><b style="font-size:10px">SAFETY</b><div style="margin-top:7px;font-size:9px;color:#7895a3;line-height:1.7">PLC WRITE: <b style="color:#ff6075">BLOCKED</b><br>SCADA CONTROL: <b style="color:#ff6075">BLOCKED</b><br>HUMAN DECISION: <b style="color:#29dfa8">REQUIRED</b></div></div>
</div></div>'''

SCRIPT = r'''<script id="ANVI_V2_RUNTIME_SCRIPT">
(function(){
if(window.__anviV2RuntimeLoaded)return; window.__anviV2RuntimeLoaded=true;
function esc(v){return String(v==null?"":v).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
async function refreshV2(){
var box=document.getElementById("anviV2Changed"); if(!box)return;
try{var r=await fetch("/api/command-centre/what-changed",{credentials:"same-origin"}),d=await r.json();
if(!r.ok){box.textContent=d.message||d.status||"V2 evidence unavailable";return;}
var items=Array.isArray(d.items)?d.items:[]; if(!items.length){box.textContent="No change evidence currently available.";return;}
box.innerHTML=items.slice(0,4).map(function(x){return "<div style='margin:3px 0'><b>"+esc(x.equipment||x.tag||"Plant")+"</b> — "+esc(x.summary||x.change_type||x.event_type||"evidence")+"</div>";}).join("");
}catch(e){box.textContent="V2 evidence temporarily unavailable";}
}
window.anviV2Correlate=function(){
var equipment=window.prompt("Equipment/tag for event correlation (example: PT-303)"); if(!equipment)return;
var box=document.getElementById("anviV2Correlation"); if(!box)return; box.textContent="Loading "+equipment+"…";
fetch("/api/command-centre/event-correlation?equipment="+encodeURIComponent(equipment),{credentials:"same-origin"}).then(function(r){return r.json().then(function(d){return {ok:r.ok,d:d};});}).then(function(x){
var d=x.d;if(!x.ok){box.textContent=d.message||d.status||"Correlation unavailable";return;}
var c=d.correlation||{};box.innerHTML="<b>"+esc(d.equipment)+"</b><br>Events: "+esc(c.event_count??(d.timeline||[]).length)+"<br><span style='color:#7895a3'>Temporal/identity association only; no physical causation claimed.</span>";
}).catch(function(){box.textContent="Event correlation temporarily unavailable";});
};
function install(){
if(document.getElementById("ANVI_V2_RUNTIME_PANEL"))return true;
var content=document.getElementById("content");if(!content)return false;
content.insertAdjacentHTML("afterbegin",'<div id="ANVI_V2_RUNTIME_PANEL" style="margin:14px 0;padding:14px;border:1px solid #193b49;border-radius:13px;background:#09151d;color:#e8f6fa;font-family:Inter,system-ui,sans-serif"><div style="font-size:9px;color:#31d8f5;letter-spacing:1.7px;font-weight:800">V2 REAL-TIME INDUSTRIAL INTELLIGENCE</div><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin-top:10px"><div style="padding:11px;border:1px solid #193b49;border-radius:9px;background:#06151f"><b style="font-size:10px">WHAT CHANGED</b><div id="anviV2Changed" style="margin-top:7px;font-size:9px;color:#7895a3">Loading scoped evidence…</div></div><div style="padding:11px;border:1px solid #193b49;border-radius:9px;background:#06151f"><b style="font-size:10px">EVENT CORRELATION</b><div id="anviV2Correlation" style="margin-top:7px;font-size:9px;color:#7895a3;cursor:pointer">Tap to inspect equipment event sequence.</div></div><div style="padding:11px;border:1px solid #193b49;border-radius:9px;background:#06151f"><b style="font-size:10px">SAFETY</b><div style="margin-top:7px;font-size:9px;color:#7895a3;line-height:1.7">PLC WRITE: <b style="color:#ff6075">BLOCKED</b><br>SCADA CONTROL: <b style="color:#ff6075">BLOCKED</b><br>HUMAN DECISION: <b style="color:#29dfa8">REQUIRED</b></div></div></div></div>');
var c=document.getElementById("anviV2Correlation");if(c)c.onclick=window.anviV2Correlate;
refreshV2();setInterval(refreshV2,30000);return true;
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",install);else install();
})();
</script>'''

@app.after_request
def inject_v2_command_centre_ui(response):
    if request.path != "/" or response.status_code != 200:return response
    if "text/html" not in response.headers.get("Content-Type",""):return response
    try:
        body=response.get_data(as_text=True)
        if MARKER in body or "</body>" not in body:return response
        body=body.replace("</body>",PANEL+SCRIPT+"</body>",1)
        response.set_data(body);response.headers.pop("Content-Length",None)
    except Exception as exc:
        print("ANVI_V2_UI_INJECTION_ERROR",repr(exc),flush=True)
    return response
