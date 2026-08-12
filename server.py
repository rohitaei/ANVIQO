from flask import Flask, request, jsonify
from anvi_orchestrator import orchestrate_equipment
import re

app = Flask(__name__)


def find_equipment_tag(text):
    """
    Detect equipment tags such as CV-101, PT-1001, FT-201, etc.
    """
    match = re.search(r'\b[A-Z]{1,5}-\d{2,6}\b', text.upper())
    return match.group(0) if match else None


def basic_anvi_answer(question):
    q = question.lower().strip()

    if not q:
        return "Please ask Anvi an Electrical or Instrumentation question."

    if "4-20 ma" in q or "4 to 20 ma" in q:
        return (
            "4–20 mA is a standard industrial analog signal. "
            "Normally 4 mA represents 0% and 20 mA represents 100%. "
            "Check transmitter supply, loop wiring, polarity, resistance "
            "and the PLC/DCS analog input."
        )

    if "rtd" in q:
        return (
            "For an RTD problem, check sensor resistance, lead wiring, "
            "terminal connections, transmitter configuration and the "
            "PLC/DCS input."
        )

    if "thermocouple" in q:
        return (
            "For a thermocouple problem, check sensor type, polarity, "
            "extension cable, cold-junction compensation and terminals."
        )

    if "dp transmitter" in q or "differential pressure" in q:
        return (
            "For a DP transmitter problem, check impulse lines, manifold "
            "valves, equalizing valve, zero condition, calibration range "
            "and 4–20 mA output."
        )

    if "control valve" in q or "valve" in q:
        return (
            "For a control-valve problem, check command signal, positioner, "
            "instrument air, I/P converter, valve travel and mechanical condition."
        )

    if "vfd" in q:
        return (
            "For a VFD fault, check the displayed fault code first. "
            "Then check incoming supply, motor connections, overload, "
            "parameters, cooling and control signals."
        )

    if "plc" in q:
        return (
            "For PLC troubleshooting, check power and CPU status first. "
            "Then check communication, inputs, outputs, interlocks and logic."
        )

    return (
        "I understand the question. Give me an equipment tag, instrument, "
        "symptom, alarm or signal value and I'll analyze it."
    )


def build_equipment_answer(result):
    equipment = result.get("equipment_data") or {}
    health = result.get("health") or {}
    trend = result.get("health_trend") or {}
    reasoning = result.get("reasoning") or {}
    evidence = result.get("evidence_context") or {}

    name = equipment.get("name", result.get("equipment", "Equipment"))
    tag = result.get("equipment", "UNKNOWN")

    risk = health.get("risk_score", reasoning.get("risk_score", "N/A"))
    status = health.get("status", "UNKNOWN")
    confidence = health.get(
        "confidence",
        reasoning.get("confidence", "N/A")
    )

    assessment = reasoning.get(
        "assessment",
        "No detailed assessment available."
    )

    first_check = reasoning.get(
        "first_check",
        "Review the latest equipment condition and trends."
    )

    recommendations = reasoning.get(
        "recommendations",
        []
    )

    # V4.11 evidence adapter returns the
    # aggregation inside the "evidence" field.
    evidence_data = evidence.get(
        "evidence",
        evidence
    )

    evidence_strength = evidence_data.get(
        "evidence_strength",
        "INSUFFICIENT DATA"
    )

    verified_actions = evidence_data.get(
        "verified_actions",
        evidence.get("verified_actions", 0)
    )

    improvement_rate = evidence_data.get(
        "improvement_rate",
        evidence.get("improvement_rate", 0)
    )

    if isinstance(improvement_rate, (int, float)):
        improvement_rate = round(improvement_rate * 100, 1)

    lines = [
        f"ANVI EQUIPMENT INTELLIGENCE — {tag}",
        "",
        f"Equipment: {name}",
        f"Status: {status}",
        f"Risk: {risk}/100",
        f"Confidence: {confidence}%",
        "",
        f"Health trend: {trend.get('status', 'UNKNOWN')}",
        "",
        "ANVI ASSESSMENT",
        assessment,
        "",
        "FIRST CHECK",
        first_check,
        "",
        "EVIDENCE",
        f"Evidence strength: {evidence_strength}",
        f"Verified actions: {verified_actions}",
        f"Improvement rate: {improvement_rate}%",
    ]

    if recommendations:
        lines.extend(["", "RECOMMENDED ACTIONS"])
        for i, item in enumerate(recommendations, 1):
            lines.append(f"{i}. {item}")

    return "\n".join(lines)


@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ANVIQO V4.11</title>

<style>
body {
    margin:0;
    font-family:Arial,sans-serif;
    background:#07111f;
    color:white;
}

.container {
    max-width:850px;
    margin:auto;
    padding:18px;
}

.header {
    text-align:center;
    padding:20px 0;
}

.logo {
    font-size:42px;
    font-weight:800;
}

.tagline {
    color:#8fb8ff;
    margin-top:5px;
}

.status {
    display:inline-block;
    margin-top:12px;
    padding:8px 14px;
    border-radius:20px;
    background:#12351f;
    color:#7dff9b;
}

.card {
    background:#111e32;
    border-radius:18px;
    padding:18px;
    margin-top:16px;
    box-shadow:0 8px 30px rgba(0,0,0,.25);
}

.chat {
    min-height:380px;
    max-height:62vh;
    overflow-y:auto;
}

.message {
    padding:14px 16px;
    border-radius:15px;
    margin:12px 0;
    line-height:1.55;
    white-space:pre-wrap;
}

.anvi {
    background:#1c2b44;
}

.user {
    background:#23466f;
    text-align:right;
}

.input-area {
    display:flex;
    gap:8px;
    margin-top:14px;
}

input {
    flex:1;
    padding:15px;
    border:0;
    border-radius:12px;
    font-size:16px;
}

button {
    padding:15px 18px;
    border:0;
    border-radius:12px;
    font-weight:bold;
}

button:active {
    transform:scale(.98);
}

.small {
    color:#91a4bd;
    font-size:13px;
    text-align:center;
    margin-top:14px;
}
</style>
</head>

<body>

<div class="container">

<div class="header">
    <div class="logo">ANVIQO</div>
    <div class="tagline">Think • Predict • Protect</div>
    <div class="status">● ANVI V4.11 ONLINE</div>
</div>

<div class="card chat" id="chat">
    <div class="message anvi">
        <b>Anvi:</b><br>
        Hello. I'm Anvi, your Electrical & Instrumentation intelligence assistant.
        Give me an equipment tag such as CV-101 to inspect its condition.
    </div>
</div>

<div class="input-area">
    <input id="question"
           placeholder="Ask Anvi or enter equipment tag..."
           onkeydown="if(event.key==='Enter') askAnvi()">
    <button onclick="askAnvi()">ASK ANVI</button>
</div>

<div class="small">
    ANVIQO V4.11 • Equipment Intelligence Prototype
</div>

</div>

<script>
async function askAnvi() {

    const input = document.getElementById("question");
    const question = input.value.trim();

    if (!question) return;

    const chat = document.getElementById("chat");

    chat.innerHTML += `
        <div class="message user">
            <b>You:</b><br>${question}
        </div>
    `;

    input.value = "";

    try {

        const response = await fetch("/ask", {
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({
                question:question
            })
        });

        const data = await response.json();

        chat.innerHTML += `
            <div class="message anvi">
                <b>Anvi:</b><br>${data.answer}
            </div>
        `;

    } catch(error) {

        chat.innerHTML += `
            <div class="message anvi">
                <b>Anvi:</b><br>
                Connection error. Please check that the ANVIQO server is running.
            </div>
        `;
    }

    chat.scrollTop = chat.scrollHeight;
}
</script>

</body>
</html>
"""


@app.route("/ask", methods=["POST"])
def ask():

    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({
            "answer": "Please ask Anvi something."
        })

    tag = find_equipment_tag(question)

    # Equipment intelligence path
    if tag:

        try:

            result = orchestrate_equipment(tag)

            if result.get("equipment_data"):

                return jsonify({
                    "answer": build_equipment_answer(result),
                    "type": "equipment_intelligence",
                    "equipment": result
                })

        except Exception as e:

            return jsonify({
                "answer": f"Anvi equipment analysis error: {str(e)}",
                "type": "error"
            })

    # Normal instrumentation assistant
    return jsonify({
        "answer": basic_anvi_answer(question),
        "type": "knowledge"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
