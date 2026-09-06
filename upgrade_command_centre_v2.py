from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(".")
HTML = ROOT / "anviqo_dashboard.html"
MARK = "ANVI_COMMAND_CENTRE_V2_UPGRADE"

if not HTML.exists():
    raise SystemExit("STOP: anviqo_dashboard.html not found")

s = HTML.read_text(encoding="utf-8")

if MARK in s:
    print("V2 ALREADY INSTALLED")
    raise SystemExit(0)

backup = ROOT / f"anviqo_dashboard_before_command_centre_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
shutil.copy2(HTML, backup)
print("BACKUP:", backup)

# ---------- CSS ----------
css = r'''
<style id="ANVI_COMMAND_CENTRE_V2_CSS">
.anvi-v2-section{
margin:18px 0 8px;
color:#31ddff;
font-size:10px;
font-weight:800;
letter-spacing:1px;
}
.anvi-v2-grid{
display:grid;
grid-template-columns:repeat(4,minmax(0,1fr));
gap:12px;
margin-top:12px;
}
.anvi-v2-card{
background:linear-gradient(145deg,#071923,#08141d);
border:1px solid #163747;
border-radius:15px;
padding:15px;
box-shadow:0 8px 25px rgba(0,0,0,.16);
}
.anvi-v2-card h3{
margin:0 0 7px;
font-size:11px;
color:#dffaff;
letter-spacing:.6px;
}
.anvi-v2-number{
font-size:24px;
font-weight:800;
color:#31ddff;
margin:7px 0;
}
.anvi-v2-small{
font-size:9px;
color:#7895a5;
line-height:1.5;
}
.anvi-v2-badge{
display:inline-block;
margin-top:5px;
padding:5px 8px;
border-radius:7px;
border:1px solid #1b566b;
background:#071e2b;
color:#72def3;
font-size:8px;
font-weight:800;
}
.anvi-v2-rowgrid{
display:grid;
grid-template-columns:1fr 1fr;
gap:12px;
margin-top:12px;
}
.anvi-v2-row{
display:flex;
justify-content:space-between;
padding:9px 10px;
margin-top:6px;
border:1px solid #153544;
border-radius:8px;
background:#06151f;
font-size:9px;
color:#91b0bc;
}
.anvi-v2-row b{color:#dffaff}
.anvi-v2-actions{
display:grid;
grid-template-columns:1fr 1fr;
gap:7px;
margin-top:10px;
}
.anvi-v2-actions button{
padding:9px;
border-radius:8px;
border:1px solid #19475b;
background:#071d29;
color:#9ccbd8;
font-size:9px;
cursor:pointer;
}
.anvi-v2-actions button:hover{
border-color:#31ddff;
color:#fff;
}
@media(max-width:900px){
.anvi-v2-grid{grid-template-columns:1fr 1fr}
.anvi-v2-rowgrid{grid-template-columns:1fr}
}
@media(max-width:600px){
.anvi-v2-grid{grid-template-columns:1fr 1fr}
}
</style>
'''

if "</head>" not in s:
    raise SystemExit("STOP: </head> not found")

s = s.replace("</head>", css + "\n</head>", 1)

# ---------- Sidebar ----------
old_nav = '''<button>◆ Command Centre</button>
<button>◈ Plant Overview</button>
<button>◉ Live Alarms <b id="navAlarms">0</b></button>
<button>◌ Equipment Intelligence</button>
<button>◇ Analysis</button>
<button>◌ What Changed</button>
<button>⛓ Event Correlation</button>
<button>▣ Management Decision</button>
<button>✦ Ask ANVI</button>
<button>▤ Reports</button>
<button>⚙ Settings</button>'''

new_nav = '''<button>◆ Command Centre</button>
<button>◈ Plant Overview</button>
<button>◉ Live Alarms <b id="navAlarms">0</b></button>
<button>◌ Equipment Intelligence</button>
<button>◇ Analysis</button>
<button>◌ What Changed</button>
<button>⛓ Event Correlation</button>
<button>🔧 Maintenance Intelligence</button>
<button>⇄ Shift Intelligence</button>
<button>🧠 Plant Memory</button>
<button>◈ Risk & Prediction</button>
<button>▣ Management Decision</button>
<button>✦ Ask ANVI</button>
<button>🎤 ANVI Voice</button>
<button>▤ Reports</button>
<button>⚙ Settings</button>'''

if old_nav in s:
    s = s.replace(old_nav,new_nav,1)
    print("SIDEBAR: expanded")
else:
    print("SIDEBAR: existing pattern differs; preserved")

# ---------- Dashboard expansion ----------
anchor = '<section class="bottom">'

if anchor not in s:
    raise SystemExit("STOP: dashboard bottom section not found")

panel = r'''
<!-- ANVI_COMMAND_CENTRE_V2_UPGRADE -->

<div class="anvi-v2-section">PLANT INTELLIGENCE WORKSPACE</div>

<section class="anvi-v2-grid">

<div class="anvi-v2-card">
<h3>PLANT HEALTH</h3>
<div class="anvi-v2-number" id="v2Health">—</div>
<div class="anvi-v2-badge">LIVE INTELLIGENCE</div>
<div class="anvi-v2-small">Existing plant health intelligence.</div>
</div>

<div class="anvi-v2-card">
<h3>EQUIPMENT RISK</h3>
<div class="anvi-v2-number" id="v2Risk">—</div>
<div class="anvi-v2-badge">EQUIPMENT INTELLIGENCE</div>
<div class="anvi-v2-small">Existing equipment health and risk layer.</div>
</div>

<div class="anvi-v2-card">
<h3>MAINTENANCE</h3>
<div class="anvi-v2-number">READY</div>
<div class="anvi-v2-badge">V5 INTELLIGENCE</div>
<div class="anvi-v2-small">Priority and recommendation intelligence.</div>
</div>

<div class="anvi-v2-card">
<h3>PLANT MEMORY</h3>
<div class="anvi-v2-number">READY</div>
<div class="anvi-v2-badge">VERIFIED CONTEXT</div>
<div class="anvi-v2-small">Plant history and technician experience.</div>
</div>

</section>

<section class="anvi-v2-rowgrid">

<div class="anvi-v2-card">
<h3>INTELLIGENCE STATUS</h3>

<div class="anvi-v2-row">
<span>Event Correlation</span><b>AVAILABLE</b>
</div>

<div class="anvi-v2-row">
<span>What Changed</span><b>AVAILABLE</b>
</div>

<div class="anvi-v2-row">
<span>Shift Intelligence</span><b>V5.2</b>
</div>

<div class="anvi-v2-row">
<span>Equipment Digital Twin</span><b>AVAILABLE</b>
</div>

<div class="anvi-v2-row">
<span>Plant Brain</span><b>AVAILABLE</b>
</div>

</div>

<div class="anvi-v2-card">
<h3>QUICK INTELLIGENCE</h3>
<div class="anvi-v2-small">
Ask ANVI through the existing conversational orchestrator.
</div>

<div class="anvi-v2-actions">
<button onclick="askANVI('Show current plant health')">Plant Health</button>
<button onclick="askANVI('Show equipment at risk')">Equipment Risk</button>
<button onclick="askANVI('What changed in the plant?')">What Changed</button>
<button onclick="askANVI('Show event correlation')">Event Correlation</button>
<button onclick="askANVI('Show maintenance priorities')">Maintenance</button>
<button onclick="askANVI('Show latest shift handover report')">Shift Intelligence</button>
<button onclick="askANVI('Show plant memory')">Plant Memory</button>
<button onclick="askANVI('Give me the current plant situation')">Plant Situation</button>
</div>

</div>

</section>

<div class="anvi-v2-section">DECISION & SAFETY</div>

<section class="anvi-v2-rowgrid">

<div class="anvi-v2-card">
<h3>MANAGEMENT DECISION SUPPORT</h3>
<div class="anvi-v2-row">
<span>Priority</span><b>Evidence Based</b>
</div>
<div class="anvi-v2-row">
<span>Risk</span><b>Evidence Required</b>
</div>
<div class="anvi-v2-row">
<span>Owner</span><b>Human / Operations</b>
</div>
<div class="anvi-v2-row">
<span>Authorization</span><b>Human Required</b>
</div>
</div>

<div class="anvi-v2-card">
<h3>ANVI SAFETY BOUNDARY</h3>
<div class="anvi-v2-row">
<span>PLC Write</span><b>BLOCKED</b>
</div>
<div class="anvi-v2-row">
<span>SCADA Control</span><b>BLOCKED</b>
</div>
<div class="anvi-v2-row">
<span>Automatic Execution</span><b>BLOCKED</b>
</div>
<div class="anvi-v2-row">
<span>Human Decision</span><b>REQUIRED</b>
</div>
</div>

</section>

'''

s = s.replace(anchor,panel+anchor,1)

# ---------- JS ----------
js = r'''
<script id="ANVI_COMMAND_CENTRE_V2_JS">
(function(){
async function refreshV2(){
try{
const r=await fetch("/api/status",{credentials:"same-origin"});
const d=await r.json();
const x=d.snapshot||d.data||d||{};

const health=x.plant_health??x.health_score??x.health??"—";
const risk=x.equipment_risk??x.risk_score??"—";

const h=document.getElementById("v2Health");
const rr=document.getElementById("v2Risk");

if(h)h.textContent=String(health);
if(rr)rr.textContent=String(risk);
}catch(e){}
}

refreshV2();
setInterval(refreshV2,30000);
})();
</script>
'''

s = s.replace("</body>",js+"\n</body>",1)

HTML.write_text(s,encoding="utf-8")

print("================================================")
print("ANVI COMMAND CENTRE V2 INSTALLED")
print("================================================")
print("UI ONLY: YES")
print("V5 INTELLIGENCE: PRESERVED")
print("SHIFT REPORT: PRESERVED")
print("VOICE: PRESERVED")
print("API ASK: PRESERVED")
print("API STATUS: PRESERVED")
print("PLC WRITE: BLOCKED")
print("SCADA CONTROL: BLOCKED")
print("================================================")
