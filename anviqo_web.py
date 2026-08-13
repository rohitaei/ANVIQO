from flask import Flask, jsonify, render_template_string, session, redirect, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = "anviqo-production-session-key"

VERSION = "ANVIQO PRODUCT V1.0"

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "automatic_authorization": False,
    "causation_claim": False,
}

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>ANVIQO | Industrial Intelligence</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #07111f;
    color: #eaf2f8;
    font-family: Arial, sans-serif;
}

.header {
    height: 70px;
    display: flex;
    align-items: center;
    padding: 0 24px;
    background: #0b1728;
    border-bottom: 1px solid #20354d;
}

.logo {
    font-size: 26px;
    font-weight: bold;
    color: #37d6e8;
}

.tagline {
    margin-left: 18px;
    color: #8ea4ba;
    font-size: 12px;
}

.time {
    margin-left: auto;
    color: #8ea4ba;
    font-size: 12px;
}

.layout {
    display: flex;
    min-height: calc(100vh - 70px);
}

.sidebar {
    width: 225px;
    background: #0c192b;
    border-right: 1px solid #20354d;
    padding: 20px 10px;
}

.sidebar-title {
    color: #6f879f;
    font-size: 11px;
    font-weight: bold;
    padding: 10px;
}

.nav {
    padding: 12px;
    margin: 3px 0;
    border-radius: 6px;
    color: #dbe7f0;
    font-size: 13px;
}

.nav:hover {
    background: #142941;
    color: #37d6e8;
}

.content {
    flex: 1;
    padding: 25px;
    overflow: auto;
}

h1 {
    margin: 0;
    font-size: 24px;
}

.subtitle {
    color: #8097ad;
    margin-top: 6px;
    font-size: 13px;
}

.cards {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-top: 25px;
}

.card {
    background: #0e1d30;
    border: 1px solid #213952;
    border-radius: 8px;
    padding: 16px;
}

.card-title {
    color: #8299af;
    font-size: 10px;
    font-weight: bold;
}

.card-value {
    margin-top: 10px;
    font-size: 20px;
    font-weight: bold;
}

.attention {
    color: #f5c542;
}

.urgent {
    color: #ff5c5c;
}

.good {
    color: #28d17c;
}

.blue {
    color: #4da3ff;
}

.cyan {
    color: #37d6e8;
}

.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
    margin-top: 15px;
}

.panel {
    background: #0e1d30;
    border: 1px solid #213952;
    border-radius: 8px;
    padding: 18px;
    min-height: 190px;
}

.panel-title {
    color: #37d6e8;
    font-size: 12px;
    font-weight: bold;
    margin-bottom: 15px;
}

.item {
    padding: 8px 0;
    border-bottom: 1px solid #172c43;
    font-size: 13px;
}

.item:last-child {
    border-bottom: none;
}

.badge {
    float: right;
    padding: 4px 7px;
    border-radius: 4px;
    background: #251d1d;
    color: #ff6b6b;
    font-size: 10px;
}

.decision {
    border-left: 3px solid #f5c542;
    padding-left: 12px;
}

.safety {
    margin-top: 15px;
    background: #0d241c;
    border: 1px solid #1d5a42;
    border-radius: 8px;
    padding: 15px;
    color: #28d17c;
    font-size: 11px;
    font-weight: bold;
}

@media(max-width:900px) {

    .sidebar {
        display: none;
    }

    .content {
        padding: 15px;
    }

    .cards {
        grid-template-columns: repeat(2, 1fr);
    }

    .grid {
        grid-template-columns: 1fr;
    }
}

</style>
</head>

<body>

<div class="header">

    <div class="logo">
        ANVIQO
    </div>

    <div class="tagline">
        THINK • PREDICT • PROTECT
    </div>

    <div class="time" id="clock">
    </div>

</div>

<div class="layout">

<div class="sidebar">

    <div class="sidebar-title">
        COMMAND CENTER
    </div>

    <div class="nav">⌂ &nbsp; Command Center</div>
    <div class="nav">◉ &nbsp; Plant Health</div>
    <div class="nav">⚙ &nbsp; Equipment</div>
    <div class="nav">⚠ &nbsp; Events & Correlation</div>
    <div class="nav">↗ &nbsp; What Changed</div>
    <div class="nav">◆ &nbsp; Maintenance</div>
    <div class="nav">⇄ &nbsp; Shift Intelligence</div>
    <div class="nav">▣ &nbsp; Management</div>
    <div class="nav">★ &nbsp; Executive / HOD</div>
    <div class="nav">✓ &nbsp; Evidence & Learning</div>

</div>

<div class="content">

    <h1>
        Plant Intelligence Command Center
    </h1>

    <div class="subtitle">
        Unified ANVIQO V5 intelligence overview
    </div>

    <div class="cards">

        <div class="card">
            <div class="card-title">
                PLANT HEALTH
            </div>
            <div class="card-value attention">
                ATTENTION
            </div>
        </div>

        <div class="card">
            <div class="card-title">
                MANAGEMENT PRIORITY
            </div>
            <div class="card-value urgent">
                P1 — URGENT
            </div>
        </div>

        <div class="card">
            <div class="card-title">
                ACTIVE RISKS
            </div>
            <div class="card-value blue">
                03
            </div>
        </div>

        <div class="card">
            <div class="card-title">
                EVENT CHAINS
            </div>
            <div class="card-value cyan">
                02
            </div>
        </div>

        <div class="card">
            <div class="card-title">
                CONFIDENCE
            </div>
            <div class="card-value good">
                88%
            </div>
        </div>

    </div>

    <div class="grid">

        <div class="panel">

            <div class="panel-title">
                TOP EQUIPMENT RISKS
            </div>

            <div class="item">
                CV-101
                <span class="badge">
                    P1 • 84.7
                </span>
            </div>

            <div class="item">
                CV-102
                <span class="badge">
                    HIGH • 71.4
                </span>
            </div>

            <div class="item">
                PT-201
                <span class="badge">
                    WARNING • 63.2
                </span>
            </div>

        </div>

        <div class="panel">

            <div class="panel-title">
                WHAT CHANGED
            </div>

            <div class="item">
                ✓ CV-101 valve position increased
            </div>

            <div class="item">
                ✓ CV-102 valve position increased
            </div>

            <div class="item">
                ✓ PT-201 pressure condition changed
            </div>

            <div class="item">
                ✓ Multiple abnormal signals detected
            </div>

        </div>

        <div class="panel">

            <div class="panel-title">
                EVENT / CORRELATION
            </div>

            <div class="item">
                CV-101 ↔ CV-102
            </div>

            <div class="item">
                PROCESS_RELATED
            </div>

            <div class="item">
                Developing event chain
            </div>

            <div class="item">
                CV-102 ↔ PT-201
            </div>

            <div class="item">
                PROCESS_RELATED
            </div>

        </div>

        <div class="panel">

            <div class="panel-title">
                MANAGEMENT DECISION
            </div>

            <div class="decision">

                <strong>
                    CV-101
                </strong>

                <p>
                    MAINTENANCE REVIEW REQUIRED
                </p>

                <p>
                    Controlled maintenance review and
                    process-condition verification recommended.
                </p>

                <strong>
                    Human authorization required
                </strong>

            </div>

        </div>

    </div>

    <div class="safety">

        ● READ-ONLY &nbsp;&nbsp;
        ● PLC WRITE BLOCKED &nbsp;&nbsp;
        ● SCADA CONTROL BLOCKED &nbsp;&nbsp;
        ● HUMAN DECISION REQUIRED &nbsp;&nbsp;
        ● AUTOMATIC AUTHORIZATION DISABLED

    </div>

</div>

</div>

<script>

function updateClock() {

    const now = new Date();

    document.getElementById("clock").innerText =
        now.toLocaleDateString() +
        "   " +
        now.toLocaleTimeString();

}

setInterval(
    updateClock,
    1000
);

updateClock();

</script>


<!-- ANVIQO VOICE INTERFACE -->
<style>
#anviVoicePanel{
    position:fixed;
    right:18px;
    bottom:18px;
    z-index:99999;
    background:rgba(15,23,42,.97);
    color:#fff;
    border:1px solid rgba(255,255,255,.18);
    border-radius:16px;
    padding:14px;
    width:310px;
    box-shadow:0 12px 40px rgba(0,0,0,.35);
    font-family:Arial,sans-serif;
}
#anviVoicePanel .av-title{
    font-weight:700;
    font-size:16px;
    margin-bottom:8px;
}
#anviVoiceButton{
    width:100%;
    border:0;
    border-radius:12px;
    padding:12px;
    cursor:pointer;
    font-weight:700;
    font-size:15px;
}
#anviVoiceButton.listening{
    outline:3px solid rgba(239,68,68,.35);
}
#anviVoiceStatus{
    margin-top:8px;
    font-size:12px;
    opacity:.9;
}
#anviVoiceTranscript{
    margin-top:8px;
    padding:8px;
    min-height:35px;
    background:rgba(255,255,255,.08);
    border-radius:8px;
    font-size:12px;
    line-height:1.4;
}
#anviVoiceResponse{
    margin-top:8px;
    padding:8px;
    background:rgba(255,255,255,.06);
    border-radius:8px;
    font-size:12px;
    line-height:1.4;
    max-height:120px;
    overflow:auto;
}
</style>

<div id="anviVoicePanel">
    <div class="av-title">🎙 ANVI Voice</div>
    <button id="anviVoiceButton" type="button">🎤 Speak to ANVI</button>
    <div id="anviVoiceStatus">Ready — same ANVI intelligence and command layer.</div>
    <div id="anviVoiceTranscript">Transcript will appear here.</div>
    <div id="anviVoiceResponse">ANVI response will appear here.</div>
</div>

<script>
(function(){
    const button = document.getElementById("anviVoiceButton");
    const status = document.getElementById("anviVoiceStatus");
    const transcript = document.getElementById("anviVoiceTranscript");
    const responseBox = document.getElementById("anviVoiceResponse");

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    let recognition = null;
    let listening = false;
    let transcriptHistory = [];

    function speak(text){
        if (!("speechSynthesis" in window)) return;
        try {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "en-IN";
            utterance.rate = 0.95;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        } catch(e) {}
    }

    function saveTranscript(question, answer){
        transcriptHistory.push({
            timestamp: new Date().toISOString(),
            technician: question,
            anvi: answer
        });

        try {
            localStorage.setItem(
                "anviqo_voice_transcript",
                JSON.stringify(transcriptHistory)
            );
        } catch(e) {}
    }

    async function askANVI(question){
        status.textContent = "ANVI is processing...";
        responseBox.textContent = "Processing...";

        try {
            const r = await fetch("/api/ask", {
                method: "POST",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({question: question})
            });

            const data = await r.json();
            const answer =
                data.answer ||
                data.message ||
                "ANVI returned no response.";

            responseBox.textContent = answer;
            saveTranscript(question, answer);
            speak(answer);

            status.textContent =
                data.control_request
                    ? "Command request created — human approval required."
                    : "ANVI response ready.";

            return data;
        } catch(e) {
            const msg = "Voice request failed: " + e.message;
            responseBox.textContent = msg;
            status.textContent = msg;
        }
    }

    if (!SpeechRecognition){
        button.disabled = true;
        button.textContent = "🎤 Voice unavailable";
        status.textContent =
            "This browser does not expose Speech Recognition. Use Chrome/Edge with microphone permission.";
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = function(){
        listening = true;
        button.classList.add("listening");
        button.textContent = "🔴 Listening...";
        status.textContent = "Listening. Speak naturally to ANVI.";
    };

    recognition.onresult = function(event){
        let finalText = "";
        let interimText = "";

        for(let i=event.resultIndex; i<event.results.length; i++){
            const t = event.results[i][0].transcript;
            if(event.results[i].isFinal) finalText += t;
            else interimText += t;
        }

        transcript.textContent =
            finalText || interimText || "Listening...";

        if(finalText.trim()){
            askANVI(finalText.trim());
        }
    };

    recognition.onerror = function(event){
        status.textContent = "Voice error: " + event.error;
    };

    recognition.onend = function(){
        listening = false;
        button.classList.remove("listening");
        button.textContent = "🎤 Speak to ANVI";
        if(!status.textContent.startsWith("ANVI")) {
            status.textContent = "Ready.";
        }
    };

    button.addEventListener("click", function(){
        if(listening){
            recognition.stop();
            return;
        }

        transcript.textContent = "Listening...";
        responseBox.textContent = "Waiting for your command...";
        recognition.start();
    });

    window.ANVIQOVoice = {
        ask: askANVI,
        speak: speak,
        getTranscript: function(){
            return transcriptHistory.slice();
        }
    };
})();
</script>
<!-- END ANVIQO VOICE INTERFACE -->

</body>
</html>
"""


@app.route("/")
def dashboard():
    return send_from_directory(".", "anviqo_public_website_index.html")


@app.route("/api/voice/capabilities")
def voice_capabilities_api():
    try:
        from anvi_voice import voice_capabilities
        return jsonify(voice_capabilities())
    except Exception as e:
        return jsonify({
            "status": "ERROR",
            "message": str(e),
            "read_only": True
        }), 500

@app.route("/api/ask", methods=["POST"])
def ask_anvi():
    from flask import request
    import json as _json

    try:
        q=(request.get_json(silent=True) or {}).get("question","").strip()
        ql=q.lower()

        with open(os.path.join("database","pci","pci_instrument_database.json"),encoding="utf-8") as f:
            db=_json.load(f)

        records=db.get("records",[])

        # ---- PCI evidence ----
        if any(k in ql for k in ["pci","at_201","at_202","pt_303","lt_302","instrument","i/o","io","critical"]):

            if "at_201" in ql or "at_202" in ql or "pt_303" in ql or "lt_302" in ql:
                for x in records:
                    tag=str(x.get("tag","")).lower()
                    if tag and tag in ql:
                        return {"answer":
                            f"ANVI PCI evidence — {x.get('tag')}: "
                            f"{x.get('description','No description')}. "
                            f"Area: {x.get('area','UNKNOWN')}. "
                            f"I/O type: {x.get('io_type','UNKNOWN')}. "
                            f"Criticality: {x.get('criticality','NOT CLASSIFIED')}."
                        }

            if "critical" in ql:
                critical=[x for x in records if x.get("criticality")=="HIGH"]
                return {"answer":
                    "ANVI PCI evidence: I found "
                    f"{len(critical)} HIGH-criticality instruments in the verified 1,064-I/O PCI database: "
                    + "; ".join(
                        f"{x.get('tag')} — {x.get('description')} ({x.get('area')})"
                        for x in critical
                    ) + "."
                }

            from collections import Counter
            io=Counter(x.get("io_type","UNKNOWN") for x in records)
            areas=Counter(x.get("area","UNKNOWN") for x in records)

            return {"answer":
                f"ANVI PCI evidence is connected. "
                f"The PCI database contains {len(records)} I/O records across {len(areas)} areas. "
                f"Distribution: " +
                ", ".join(f"{k}: {v}" for k,v in io.items()) +
                ". The database is read-only and does not authorize PLC/SCADA control."
            }

        return {"answer":
            "ANVI is online and connected to the V5 Frozen intelligence product. "
            "I can answer PCI questions, equipment questions, plant-condition questions, "
            "events, maintenance and management-intelligence questions."
        }

    except Exception as e:
        return {"answer":"ANVI evidence service error: "+str(e)}

@app.route("/api/status")
def status():

    return jsonify({

        "product": "ANVIQO",

        "version": VERSION,

        "status": "READY",

        "core": "V5 FROZEN",

        "safety": SAFETY,

        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            )
    })


@app.route("/health")
def health():

    return jsonify({

        "status": "OK",

        "product": "ANVIQO",

        "version": VERSION

    })


if __name__ == "__main__":

    print("=" * 68)
    print("        ANVIQO PRODUCT WEB SERVER")
    print("=" * 68)
    print()
    print("Version :", VERSION)
    print("Core    : V5 FROZEN")
    print("Mode    : READ-ONLY")
    print()
    print("Dashboard:")
    print("http://127.0.0.1:5000")
    print()
    print("API:")
    print("http://127.0.0.1:5000/api/status")
    print()
    print("Health:")
    print("http://127.0.0.1:5000/health")
    print("=" * 68)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
