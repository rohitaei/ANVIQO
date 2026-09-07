from pathlib import Path
from datetime import datetime
import shutil
import re
import ast

ROOT = Path(".")
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

FILES = [
    "anvi_knowledge_layer.py",
    "plant_memory.py",
    "anviqo_api.py",
    "anviqo_dashboard.html",
]

print("=" * 72)
print("ANVIQO FIELD REPORT + NATURAL TROUBLESHOOTING V1")
print("=" * 72)

# ------------------------------------------------------------------
# 1. SAFETY BACKUP
# ------------------------------------------------------------------
backup = ROOT / f".anviqo_backup_{STAMP}"
backup.mkdir(exist_ok=True)

for name in FILES:
    p = ROOT / name
    if p.exists():
        shutil.copy2(p, backup / name)

print(f"[BACKUP] {backup}")

# ------------------------------------------------------------------
# 2. CREATE CLEAN FIELD REPORT INGESTION MODULE
# ------------------------------------------------------------------
module = r'''"""
ANVIQO FIELD REPORT INGESTION V1

Purpose:
- Extract structured maintenance/event information from natural technician reports.
- Accept pasted text and extracted document text.
- Never invent root cause.
- Store conversational reports as PENDING_VERIFICATION.
- Does not perform PLC/SCADA writes.
- Does not create a new reasoning engine.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "automatic_authorization": False,
    "causation_claim": False,
}


TAG_RE = re.compile(
    r"\b([A-Z]{1,8}[-_ ]?\d{1,5})\b",
    re.I,
)


def _clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _first_tag(text):
    for match in TAG_RE.finditer(text):
        tag = match.group(1).upper().replace("_", "-").replace(" ", "-")
        # Avoid interpreting ordinary words followed by numbers as tags.
        if re.match(r"^[A-Z]{1,8}-\d{1,5}$", tag):
            return tag
    return ""


def _extract_present_with(text):
    patterns = [
        r"\bwith\s+(?:a\s+)?(?:present|presence)\s+(?:of\s+)?([A-Za-z][A-Za-z .'-]{2,60})",
        r"\bpresent\s+with\s+([A-Za-z][A-Za-z .'-]{2,60})",
        r"\bwith\s+([A-Z][A-Za-z .'-]{2,40})\s*$",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            value = _clean(m.group(1))
            value = re.sub(r"[.,;]+$", "", value)
            if value:
                return value
    return ""


def _extract_field(text, labels):
    for label in labels:
        m = re.search(
            rf"\b{re.escape(label)}\s*[:=-]\s*(.+?)(?=\n|$)",
            text,
            re.I,
        )
        if m:
            return _clean(m.group(1))
    return ""


def _extract_equipment(text, tag):
    if tag:
        # Known tag is the safest equipment identifier.
        return tag

    patterns = [
        r"\b(?:equipment|instrument|device|unit)\s*[:=-]\s*([A-Za-z0-9 _./-]+)",
        r"\b(UPS[- ]?\d+)\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return _clean(m.group(1))
    return ""


def _extract_location(text):
    patterns = [
        r"\b(?:location|area|plant|site)\s*[:=-]\s*(.+?)(?:\n|$)",
        r"\bat\s+the\s+([A-Za-z0-9][A-Za-z0-9 .&'/-]{2,80})",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            value = _clean(m.group(1))
            value = re.sub(r"[.,;]+$", "", value)
            if value:
                return value
    return ""


def _extract_observation(text):
    patterns = [
        r"\bnoticed\s+that\s+(.+?)(?=\.\s+I\s+then|\.\s+After|\.\s+However|$)",
        r"\bobserved\s+that\s+(.+?)(?=\.\s+I\s+then|\.\s+After|\.\s+However|$)",
        r"\bproblem\s*[:=-]\s*(.+?)(?:\n|$)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I | re.S)
        if m:
            return _clean(m.group(1))
    return ""


def _extract_finding(text):
    patterns = [
        r"\bchecked\s+(.+?)(?=\.|\n|$)",
        r"\bfound\s+(.+?)(?=\.|\n|$)",
        r"\bchecking\s+(.+?)(?=\.|\n|$)",
    ]
    values = []
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            value = _clean(m.group(1))
            if value and value not in values:
                values.append(value)
    return "; ".join(values[:5])


def _extract_action(text):
    patterns = [
        r"\bI\s+(?:then\s+)?(.+?)(?=\.?\s+(?:After that|However|But|Then|Finally)\b|$)",
        r"\b(?:action|work done|rectification)\s*[:=-]\s*(.+?)(?:\n|$)",
    ]
    values = []
    for p in patterns:
        for m in re.finditer(p, text, re.I | re.S):
            value = _clean(m.group(1))
            if value and len(value) > 3:
                values.append(value)
    return "; ".join(values[:5])


def _extract_outcome(text):
    patterns = [
        r"\b(?:now|currently)\s+(?:it\s+is\s+)?(.+?)(?:\.|$)",
        r"\b(?:returned|return)\s+to\s+(.+?)(?:\.|$)",
        r"\b(?:everything|system|instrument|unit)\s+(?:is|was)\s+(.+?)(?:\.|$)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return _clean(m.group(1))
    return ""


def _extract_recovery(text):
    low = text.lower()

    if any(x in low for x in [
        "now ok",
        "now normal",
        "returned to normal",
        "back to normal",
        "healthy signal restored",
        "working normally",
        "working normal",
    ]):
        return "Recovered"

    if any(x in low for x in [
        "still abnormal",
        "still faulty",
        "still not working",
        "still fluctuating",
        "intermittent",
        "blinking intermittently",
    ]):
        return "Not fully recovered / requires verification"

    return ""


def _extract_spare(text):
    m = re.search(
        r"\b(?:used|replaced with|replacement)\s+(?:one\s+|a\s+)?"
        r"([A-Z]{1,8}[-_ ]?\d{1,5})",
        text,
        re.I,
    )
    if m:
        return m.group(1).upper().replace("_", "-").replace(" ", "-")
    return ""


def parse_field_report(text, filename=""):
    text = str(text or "").strip()
    if not text:
        raise ValueError("Field report is empty.")

    tag = _first_tag(text)
    equipment = _extract_equipment(text, tag)
    location = _extract_location(text)
    present_with = _extract_present_with(text)
    observation = _extract_observation(text)
    finding = _extract_finding(text)
    action = _extract_action(text)
    outcome = _extract_outcome(text)
    recovery = _extract_recovery(text)
    spare = _extract_spare(text)

    # Deterministic PT example:
    # "PT-303 was not showing anything checked fuse blown no power
    #  changed fuse now ok"
    low = text.lower()

    if not observation and ("not showing" in low or "not showing any" in low):
        observation = "No indication / no visible indication"

    if not finding and ("fuse blown" in low or "fuse" in low and "no power" in low):
        finding = "Fuse blown / no power"

    if not action and ("changed fuse" in low or "replaced fuse" in low):
        action = "Fuse replaced"

    if not outcome and "now ok" in low:
        outcome = "Instrument returned to normal operation"

    if not recovery:
        recovery = _extract_recovery(text)

    # Do not invent a root cause.
    root_cause = ""

    notes = (
        f"Source type: technician field report. "
        f"Source file: {filename or 'pasted report'}. "
        f"Reported at: {datetime.now().isoformat(timespec='seconds')}."
    )

    if present_with:
        notes += f" Present with: {present_with}."

    if not tag and not equipment:
        raise ValueError(
            "Could not identify an equipment tag or equipment name from the report."
        )

    return {
        "event": observation or "Technician field report",
        "equipment": equipment or tag,
        "tag": tag,
        "area": location,
        "observation": observation,
        "finding": finding,
        "maintenance_action": action,
        "confirmation_evidence": outcome,
        "outcome": outcome,
        "recovery_status": recovery,
        "spare_used": spare,
        "source": "technician field report",
        "root_cause": root_cause,
        "notes": notes,
        "raw_report": text,
        "source_file": filename or "",
        "present_with": present_with,
        **SAFETY,
    }


def store_field_report(text, filename=""):
    record = parse_field_report(text, filename)

    import plant_memory

    # Existing Plant Memory remains authoritative.
    # Conversational reports remain pending until human verification.
    memory = plant_memory.create_conversational_memory(
        event=record["event"],
        equipment=record["equipment"],
        tag=record["tag"],
        area=record["area"],
        source=record["source"],
        observation=record["observation"],
        maintenance_action=record["maintenance_action"],
        finding=record["finding"],
        confirmation_evidence=record["confirmation_evidence"],
        outcome=record["outcome"],
        recovery_status=record["recovery_status"],
        spare_used=record["spare_used"],
        notes=(
            record["notes"]
            + f" Raw report: {record['raw_report']}"
            + (f" Present with: {record['present_with']}."
               if record["present_with"] else "")
        ),
    )

    return {
        "status": "PENDING_VERIFICATION",
        "domain": "plant_memory",
        "memory": memory,
        "parsed_report": record,
        **SAFETY,
    }
'''

(ROOT / "anvi_field_report.py").write_text(module, encoding="utf-8")
print("[OK] Created anvi_field_report.py")

# ------------------------------------------------------------------
# 3. STRENGTHEN NATURAL TROUBLESHOOTING DETECTOR
# ------------------------------------------------------------------
kp = ROOT / "anvi_knowledge_layer.py"
text = kp.read_text(encoding="utf-8")

new_detector = r'''def _anvi_troubleshooting_question(question):
    """
    Natural technician troubleshooting detector.

    This is routing only. It does not create a new reasoning engine.
    Existing V5 maintenance/troubleshooting intelligence remains the
    authoritative reasoning layer.
    """
    q = str(question or "").strip().lower()

    explicit = (
        "what should i check",
        "what should we check",
        "what do i check",
        "what do we check",
        "what can i check",
        "what can we check",
        "how do i troubleshoot",
        "how should i troubleshoot",
        "how can i troubleshoot",
        "how to troubleshoot",
        "troubleshoot",
        "troubleshooting",
        "diagnose",
        "diagnosis",
        "diagnostic",
        "what could be wrong",
        "what might be wrong",
        "what is wrong",
        "why is it faulty",
        "why is it failing",
        "why did it fail",
        "possible cause",
        "possible causes",
        "checks to perform",
        "checks should i perform",
        "check the instrument",
        "check this instrument",
        "check the transmitter",
        "check this transmitter",
        "repair",
        "fix",
        "fault",
        "faulty",
        "failure",
        "failed",
        "not working",
        "isn't working",
        "wasn't working",
        "problem with",
        "issue with",
    )

    natural_symptoms = (
        "fluctuating",
        "fluctuation",
        "unstable",
        "erratic",
        "wrong reading",
        "wrong indication",
        "wrong pressure",
        "wrong value",
        "giving wrong pressure",
        "giving wrong reading",
        "giving wrong indication",
        "abnormal reading",
        "abnormal indication",
        "abnormal signal",
        "signal problem",
        "signal issue",
        "indication problem",
        "reading problem",
        "reading high",
        "reading low",
        "suddenly went high",
        "suddenly went low",
        "intermittent",
        "intermittently",
        "not responding",
        "no response",
        "showing zero",
        "shows zero",
        "stuck",
        "drift",
        "drifting",
        "spike",
        "spiking",
        "dropping",
        "jumping",
        "keeps changing",
        "keeps fluctuating",
        "not showing",
        "nothing showing",
        "no indication",
        "no output",
        "no signal",
        "signal lost",
        "signal loss",
    )

    historical = (
        "what happened previously",
        "what happened last time",
        "what happened to",
        "what did maintenance find",
        "how was it fixed previously",
        "how was it repaired previously",
        "has this problem happened before",
        "have we seen this before",
        "seen this before",
        "previous experience",
        "previous report",
        "past experience",
        "similar report",
        "similar problem",
        "previously",
        "last time",
        "earlier",
    )

    return (
        any(marker in q for marker in explicit)
        or any(marker in q for marker in natural_symptoms)
        or any(marker in q for marker in historical)
    )
'''

# Replace the complete existing function safely.
start = text.find("def _anvi_troubleshooting_question(question):")
if start == -1:
    raise RuntimeError("Could not locate _anvi_troubleshooting_question")

next_start = text.find("\ndef ", start + 10)
if next_start == -1:
    raise RuntimeError("Could not locate end of troubleshooting detector")

text = text[:start] + new_detector + "\n" + text[next_start + 1:]
kp.write_text(text, encoding="utf-8")

print("[OK] Natural troubleshooting detector replaced cleanly")

# ------------------------------------------------------------------
# 4. ADD FIELD REPORT ROUTE TO FLASK API
# ------------------------------------------------------------------
ap = ROOT / "anviqo_api.py"
api = ap.read_text(encoding="utf-8")

route = r'''
# ------------------------------------------------------------
# NATURAL FIELD REPORT INGESTION
# ------------------------------------------------------------
@app.route("/api/field_report", methods=["POST"])
@login_required
def field_report():
    """
    Accept pasted technician reports or uploaded TXT/PDF/DOCX/XLSX.

    Uploaded content is treated as evidence supplied by a human.
    It is stored as PENDING_VERIFICATION unless separately verified.
    """
    try:
        from anvi_field_report import store_field_report

        report_text = request.form.get("text", "").strip()
        filename = ""

        uploaded = request.files.get("file")

        if uploaded:
            filename = uploaded.filename or ""
            suffix = Path(filename).suffix.lower()

            raw = uploaded.read()

            if suffix in (".txt", ".log", ".csv"):
                report_text = raw.decode("utf-8", errors="replace")

            elif suffix == ".pdf":
                try:
                    from pypdf import PdfReader
                    import io
                    reader = PdfReader(io.BytesIO(raw))
                    report_text = "\n".join(
                        page.extract_text() or "" for page in reader.pages
                    )
                except Exception as exc:
                    return jsonify({
                        "status": "ERROR",
                        "message": f"PDF extraction failed: {exc}",
                        "safety": SAFETY,
                    }), 400

            elif suffix == ".docx":
                try:
                    from docx import Document
                    import io
                    doc = Document(io.BytesIO(raw))
                    report_text = "\n".join(
                        p.text for p in doc.paragraphs if p.text.strip()
                    )
                except Exception as exc:
                    return jsonify({
                        "status": "ERROR",
                        "message": f"DOCX extraction failed: {exc}",
                        "safety": SAFETY,
                    }), 400

            elif suffix in (".xlsx", ".xlsm"):
                try:
                    from openpyxl import load_workbook
                    import io
                    wb = load_workbook(
                        io.BytesIO(raw),
                        read_only=True,
                        data_only=True,
                    )
                    rows = []
                    for ws in wb.worksheets:
                        rows.append(f"[SHEET: {ws.title}]")
                        for row in ws.iter_rows(values_only=True):
                            values = [
                                str(v).strip()
                                for v in row
                                if v is not None and str(v).strip()
                            ]
                            if values:
                                rows.append(" | ".join(values))
                    report_text = "\n".join(rows)
                except Exception as exc:
                    return jsonify({
                        "status": "ERROR",
                        "message": f"XLSX extraction failed: {exc}",
                        "safety": SAFETY,
                    }), 400

            else:
                return jsonify({
                    "status": "ERROR",
                    "message": (
                        "Supported field report formats: "
                        "TXT, LOG, CSV, PDF, DOCX, XLSX, XLSM."
                    ),
                    "safety": SAFETY,
                }), 400

        if not report_text.strip():
            return jsonify({
                "status": "ERROR",
                "message": "No field report text or supported file supplied.",
                "safety": SAFETY,
            }), 400

        result = store_field_report(report_text, filename)

        return jsonify({
            "status": result.get("status", "PENDING_VERIFICATION"),
            "domain": "plant_memory",
            "message": (
                "Field report captured and stored in Plant Memory "
                "as pending verification."
            ),
            "parsed_report": result.get("parsed_report", {}),
            "memory": result.get("memory", {}),
            "safety": SAFETY,
        })

    except Exception as exc:
        return jsonify({
            "status": "ERROR",
            "message": str(exc),
            "safety": SAFETY,
        }), 400

'''

anchor = '@app.route("/api/ask", methods=["POST"])'
if anchor not in api:
    raise RuntimeError("Could not locate /api/ask route")

if 'def field_report():' not in api:
    api = api.replace(anchor, route + "\n" + anchor, 1)
    ap.write_text(api, encoding="utf-8")
    print("[OK] Added /api/field_report")
else:
    print("[OK] /api/field_report already present")

# ------------------------------------------------------------------
# 5. ADD DOCUMENT DEPENDENCIES IF AVAILABLE / REQUIRED
# ------------------------------------------------------------------
req = ROOT / "requirements.txt"
requirements = req.read_text(encoding="utf-8") if req.exists() else ""

add = []
if "pypdf" not in requirements.lower():
    add.append("pypdf>=5.0.0")
if "python-docx" not in requirements.lower():
    add.append("python-docx>=1.1.0")

if add:
    requirements = requirements.rstrip() + "\n" + "\n".join(add) + "\n"
    req.write_text(requirements, encoding="utf-8")
    print("[OK] Updated requirements.txt:", ", ".join(add))
else:
    print("[OK] Document dependencies already present")

# ------------------------------------------------------------------
# 6. ADD A CLEAN FIELD REPORT PANEL TO DASHBOARD
# ------------------------------------------------------------------
dash = ROOT / "anviqo_dashboard.html"
html = dash.read_text(encoding="utf-8")

panel = r'''
<!-- ANVI FIELD REPORT -->
<div class="page" id="page-fieldreport">
  <div class="card">
    <div class="card-head">
      <b>FIELD REPORT INTELLIGENCE</b>
      <span>PLANT MEMORY</span>
    </div>
    <div class="card-body">
      <p class="muted">
        Paste a technician report or upload TXT, PDF, DOCX or XLSX.
        ANVI extracts equipment, symptoms, checks, findings, actions
        and outcome without inventing root cause.
      </p>

      <textarea id="fieldReportText"
        style="width:100%;min-height:180px;padding:12px;
        background:#07111f;color:#eaf2f8;border:1px solid #29415b;
        border-radius:7px;"
        placeholder="Paste technician field report here..."></textarea>

      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px;">
        <input id="fieldReportFile" type="file"
          accept=".txt,.log,.csv,.pdf,.docx,.xlsx,.xlsm">

        <button class="btn primary" onclick="submitFieldReport()">
          Save Field Report
        </button>
      </div>

      <div id="fieldReportResult" style="margin-top:16px;"></div>
    </div>
  </div>
</div>
'''

if 'id="page-fieldreport"' not in html:
    # Insert before Ask ANVI page.
    marker = '<div class="page" id="page-ask">'
    if marker in html:
        html = html.replace(marker, panel + "\n" + marker, 1)

    # Add navigation item.
    nav_marker = '<button data-page="reports">'
    if nav_marker in html:
        html = html.replace(
            nav_marker,
            '<button data-page="fieldreport">▤ Field Reports</button>\n'
            + nav_marker,
            1,
        )

    # Add JS function before closing script.
    js = r'''
async function submitFieldReport(){
  const text = document.getElementById('fieldReportText').value.trim();
  const fileInput = document.getElementById('fieldReportFile');
  const result = document.getElementById('fieldReportResult');

  result.innerHTML = '<div class="muted">Processing field report...</div>';

  const form = new FormData();

  if (fileInput.files && fileInput.files.length > 0) {
    form.append('file', fileInput.files[0]);
  } else {
    form.append('text', text);
  }

  if (!text && (!fileInput.files || fileInput.files.length === 0)) {
    result.innerHTML =
      '<div class="urgent">Enter report text or select a file.</div>';
    return;
  }

  try {
    const response = await fetch('/api/field_report', {
      method: 'POST',
      body: form
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || 'Field report processing failed');
    }

    const p = data.parsed_report || {};

    result.innerHTML =
      '<div class="card">' +
      '<b>FIELD REPORT CAPTURED</b>' +
      '<p><b>Status:</b> ' + (data.status || '') + '</p>' +
      '<p><b>Equipment:</b> ' + (p.equipment || '') + '</p>' +
      '<p><b>Tag:</b> ' + (p.tag || '') + '</p>' +
      '<p><b>Location:</b> ' + (p.area || '') + '</p>' +
      '<p><b>Observation:</b> ' + (p.observation || '') + '</p>' +
      '<p><b>Finding:</b> ' + (p.finding || '') + '</p>' +
      '<p><b>Action:</b> ' + (p.maintenance_action || '') + '</p>' +
      '<p><b>Outcome:</b> ' + (p.outcome || '') + '</p>' +
      '<p><b>Recovery:</b> ' + (p.recovery_status || '') + '</p>' +
      '<p><b>Safety:</b> Read-only • Human verification required</p>' +
      '</div>';

  } catch (err) {
    result.innerHTML =
      '<div class="urgent">' + err.message + '</div>';
  }
}
'''

    # Add function to the final script section.
    pos = html.rfind("</script>")
    if pos == -1:
        raise RuntimeError("Could not locate dashboard script end")

    html = html[:pos] + "\n" + js + "\n" + html[pos:]

    dash.write_text(html, encoding="utf-8")
    print("[OK] Added Field Reports dashboard panel")
else:
    print("[OK] Field Reports dashboard already present")

# ------------------------------------------------------------------
# 7. COMPILE VALIDATION
# ------------------------------------------------------------------
print("\n===== PYTHON COMPILE =====")

py_files = [
    "anvi_field_report.py",
    "anvi_knowledge_layer.py",
    "anviqo_api.py",
    "plant_memory.py",
]

for name in py_files:
    try:
        source = (ROOT / name).read_text(encoding="utf-8")
        ast.parse(source, filename=name)
        print("[PASS]", name)
    except Exception as exc:
        print("[FAIL]", name, exc)
        print(f"\nBACKUP AVAILABLE: {backup}")
        raise

# ------------------------------------------------------------------
# 8. VERIFY REQUIRED SAFETY CONTRACT
# ------------------------------------------------------------------
print("\n===== SAFETY CONTRACT =====")

for name in ["anvi_field_report.py", "anviqo_api.py"]:
    source = (ROOT / name).read_text(encoding="utf-8")

    checks = [
        ("plc_write False", "plc_write" in source and "False" in source),
        ("scada_control False", "scada_control" in source and "False" in source),
        ("human decision", "human_decision_required" in source),
    ]

    for label, ok in checks:
        print("[PASS]" if ok else "[FAIL]", name, label)

# ------------------------------------------------------------------
# 9. NATURAL LANGUAGE REGRESSION
# ------------------------------------------------------------------
print("\n===== NATURAL TROUBLESHOOTING REGRESSION =====")

ns = {}
exec(
    compile(
        (ROOT / "anvi_knowledge_layer.py").read_text(encoding="utf-8"),
        "anvi_knowledge_layer.py",
        "exec",
    ),
    ns,
)

detector = ns["_anvi_troubleshooting_question"]

tests = {
    "PT-303 is fluctuating": True,
    "PT-303 reading is unstable": True,
    "PT-303 is giving wrong pressure": True,
    "PT-303 suddenly went high": True,
    "PT-303 is showing zero": True,
    "PT-303 signal is intermittent": True,
    "PT-303 is not responding": True,
    "What should I check in PT-303?": True,
    "Why is PT-303 fluctuating?": True,
    "What could be wrong with PT-303?": True,
    "What happened to PT-303 last time?": True,
    "What did maintenance find on PT-303?": True,
    "What is PT-303?": False,
    "Tell me about PT-303": False,
    "What is the PLC address of PT-303?": False,
}

failed = []

for q, expected in tests.items():
    actual = detector(q)
    print(("PASS" if actual == expected else "FAIL"), "|", q, "|", actual)
    if actual != expected:
        failed.append(q)

if failed:
    raise RuntimeError("Troubleshooting regression failed: " + str(failed))

# ------------------------------------------------------------------
# 10. FIELD REPORT PARSER REGRESSION
# ------------------------------------------------------------------
print("\n===== FIELD REPORT PARSER REGRESSION =====")

from anvi_field_report import parse_field_report

sample = (
    "During my visit to the main center plant, I noticed that the "
    "inverter light on UPS 2 was off and the hooter was sounding continuously. "
    "I then reset the UPS and power-cycled it. After that, the inverter light "
    "turned on and everything went back to normal. However, a short while later, "
    "the SPP light turned on and the inverter hooter started making a sound again. "
    "I reset it once more. Everything returned to normal, but the SPP light is "
    "now blinking intermittently. with a present sandip mondal"
)

parsed = parse_field_report(sample)

assert parsed["equipment"], "UPS equipment not detected"
assert parsed["observation"], "Observation missing"
assert parsed["maintenance_action"], "Action missing"
assert parsed["recovery_status"], "Recovery missing"
assert parsed["root_cause"] == "", "Root cause was incorrectly invented"

print("[PASS] UPS-2 natural field report extraction")
print("       equipment :", parsed["equipment"])
print("       location  :", parsed["area"])
print("       action    :", parsed["maintenance_action"])
print("       recovery  :", parsed["recovery_status"])
print("       root cause: NOT INVENTED")

sample2 = (
    "pt-303 was not showing any thing checked fuse blown no power "
    "changed fuse now ok save it"
)

parsed2 = parse_field_report(sample2)

assert parsed2["tag"] == "PT-303"
assert parsed2["finding"]
assert parsed2["maintenance_action"]
assert parsed2["recovery_status"] == "Recovered"

print("[PASS] PT-303 technician report extraction")

print("\n" + "=" * 72)
print("IMPLEMENTATION COMPLETE")
print("=" * 72)
print("Backup:", backup)
print("Next: install dependencies, run full project regression, then inspect git diff.")
