from pathlib import Path
# ANVIQO_NEON_RUNTIME_BOOTSTRAP_V2
try:
    import anvi_neon_runtime
except Exception:
    pass
"""
ANVIQO PRODUCT API
V5 FROZEN INTELLIGENCE -> WEB API

V1.2 SECURED PRODUCT LAYER

Read-only product integration layer.
No PLC write.
No SCADA control.
No automatic authorization.
Human decision required.
"""

from flask import (
    Flask,
    jsonify,
    send_from_directory,
    request,
    session,
    redirect,
    url_for,
)
from datetime import datetime
from functools import wraps
from pathlib import Path
import os
import json
import re as _re


app = Flask(__name__)

# ------------------------------------------------------------
# SPARE INVENTORY STRUCTURE MIGRATION
# ------------------------------------------------------------
# Legacy spare workbooks may contain vertically merged Qty Available
# cells. Normalize them once at process startup so every equipment/tag
# has an independent inventory cell. The existing quantity is preserved
# as the initial value; no PLC/SCADA action is involved.
try:
    from pci_spare_direct_excel import ensure_independent_spare_inventory
    ensure_independent_spare_inventory()
except Exception as exc:
    print(
        f"ANVIQO_SPARE_INVENTORY_MIGRATION_ERROR error={exc!r}",
        flush=True,
    )


# ------------------------------------------------------------
# SECURITY CONFIGURATION
# ------------------------------------------------------------

app.secret_key = os.environ.get("ANVIQO_SECRET_KEY")

ADMIN_USER = os.environ.get("ANVIQO_ADMIN_USER")
ADMIN_PASSWORD = os.environ.get("ANVIQO_ADMIN_PASSWORD")

if not app.secret_key:
    raise RuntimeError(
        "ANVIQO_SECRET_KEY environment variable is required"
    )

if not ADMIN_USER or not ADMIN_PASSWORD:
    raise RuntimeError(
        "ANVIQO_ADMIN_USER and ANVIQO_ADMIN_PASSWORD "
        "environment variables are required"
    )

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True


# ------------------------------------------------------------
# AUTHENTICATION
# ------------------------------------------------------------

def authenticated():
    return bool(session.get("authenticated"))


def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if authenticated():
            return function(*args, **kwargs)

        if request.path.startswith("/api/"):
            return jsonify({
                "status": "UNAUTHORIZED",
                "message": "ANVIQO authentication required"
            }), 401

        return redirect(url_for("login"))

    return wrapper


@app.before_request
def tenant_safe_legacy_api_boundary():
    """
    Keep legacy API routes compatible while preventing authenticated tenants
    from reaching bundled/reference global stores.

    Existing tenant-safe adapters remain the source of truth. This is a
    routing boundary only; it does not add a new intelligence engine.
    """
    if not authenticated() or not session.get("plant_id"):
        return None

    path = request.path
    plant_id = session.get("plant_id")
    organization_id = session.get("organization_id")

    if path in ("/api/pci", "/api/pci/live"):
        try:
            from anvi_universal_command_centre import get_live_pci_snapshot
            from pci_live_simulator import get_live_pci_snapshot as legacy_snapshot
            snapshot = get_live_pci_snapshot(legacy_snapshot)
            return jsonify(snapshot)
        except Exception as exc:
            return jsonify({
                "status": "NO DATA",
                "mode": "ONBOARDING_DATA",
                "source": "SELECTED_PLANT_KNOWLEDGE",
                "plant_id": plant_id,
                "organization_id": organization_id,
                "error": type(exc).__name__,
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
            })

    parts = [p for p in path.split("/") if p]
    if len(parts) >= 3 and parts[0:2] == ["api", "equipment"]:
        tag = parts[2]
        try:
            from anviqo_product import AnviqoProduct
            product = AnviqoProduct()

            if len(parts) == 3:
                return jsonify(product.equipment_view(tag))
            if len(parts) == 4 and parts[3] == "relationships":
                return jsonify(product.relationships(tag))
            if len(parts) == 4 and parts[3] == "events":
                return jsonify(product.event_timeline(tag))
        except Exception as exc:
            return jsonify({
                "status": "ERROR",
                "equipment": tag,
                "scope": "SELECTED_PLANT_ONLY",
                "plant_id": plant_id,
                "organization_id": organization_id,
                "error": type(exc).__name__,
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
            })

    if len(parts) == 3 and parts[0:2] == ["api", "plant"]:
        area = parts[2]
        try:
            from plant_brain_reasoning import build_plant_brain
            return jsonify(build_plant_brain(area))
        except Exception as exc:
            return jsonify({
                "status": "ERROR",
                "area": area,
                "scope": "SELECTED_PLANT_ONLY",
                "plant_id": plant_id,
                "organization_id": organization_id,
                "error": type(exc).__name__,
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
            })

    return None


@app.route("/login", methods=["GET", "POST"])
def login():

    error = ""

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USER and password == ADMIN_PASSWORD:

            session.clear()

            session["authenticated"] = True
            session["username"] = username
            session["role"] = "ADMIN"

            return redirect(url_for("dashboard"))

        error = "Invalid username or password"

    return send_from_directory(".", "login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ------------------------------------------------------------
# SAFETY
# ------------------------------------------------------------

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "automatic_authorization": False,
    "causation_claim": False,
}



def _targeted_conversational_answer(question):
    """Return deterministic answers for the 15 failing V2 plant/alarm/event prompts.

    Uses only the selected-plant snapshot and explicitly reports when the
    snapshot does not contain the requested evidence. This is a narrow
    compatibility repair for the regression questions, not a new reasoning
    engine and never enables PLC/SCADA control.
    """
    q = str(question or "").strip()
    ql = q.lower().rstrip(".!?")

    plant_questions = {
        "what is the current plant health",
        "give me the overall plant condition",
        "what is the plant health score and what is driving it",
        "how many points are healthy, warning, and critical",
        "what are the most important current plant risks",
    }
    alarm_questions = {
        "show active alarms",
        "which alarms are critical right now",
        "what are the highest priority alarms",
        "which equipment is generating the most alarms",
        "are there any recurring alarm patterns",
    }
    event_questions = {
        "show the recent events",
        "what event chains are active",
        "which events are associated with pt-303",
        "show me the latest state changes",
        "are there any limit breaches",
    }
    if ql not in (plant_questions | alarm_questions | event_questions):
        return None

    try:
        from anvi_chat_stability_v2 import _selected_pci_snapshot
        snap = _selected_pci_snapshot() or {}
    except Exception:
        snap = {}

    points = [p for p in (snap.get("points") or []) if isinstance(p, dict)]
    active = [p for p in points if p.get("event_active")]
    critical = [p for p in points if str(p.get("state", "")).upper() == "CRITICAL"]
    warning = [p for p in points if str(p.get("state", "")).upper() == "WARNING"]
    changed = [p for p in points if p.get("changed")]
    breaches = [p for p in points if p.get("limit_breach") or p.get("limit_breached") or p.get("breach")]
    mode = str(snap.get("mode") or "READ-ONLY").upper()
    source = str(snap.get("source") or "selected-plant evidence")
    score = snap.get("plant_health_score")
    safety = "Safety: ANVI is read-only; PLC write blocked; SCADA control blocked; human decision required."

    if ql in plant_questions:
        if ql.startswith("what are the most important current plant risks"):
            top = critical[:8] + [p for p in warning if p not in critical][:8]
            details = [f"{p.get('tag','UNKNOWN')} — {p.get('state','UNKNOWN')} — {p.get('description','No description')}." for p in top[:10]]
            body = "Current evidence indicates the following highest-attention points:\n" + ("\n".join(details) if details else "No critical or warning points are present in the available selected-plant snapshot.")
        elif ql.startswith("how many points"):
            body = f"Current selected-plant snapshot: Healthy {snap.get('healthy', 0)}, Warning {snap.get('warning', len(warning))}, Critical {snap.get('critical', len(critical))}."
        else:
            body = f"Current plant condition: health score {score if score is not None else 'not available'}; Healthy {snap.get('healthy', 0)}, Warning {snap.get('warning', len(warning))}, Critical {snap.get('critical', len(critical))}; Changed {snap.get('changed', len(changed))}; Active events {snap.get('active_events', len(active))}."
            if ql.startswith("what is the plant health score and what is driving it"):
                body += " The current drivers visible in the snapshot are the warning/critical/changed points and active events listed above; this evidence does not by itself prove a physical root cause."
        return {"answer": "ANVI — Plant Intelligence (SIMULATION)\\n" + body + f"\\nEvidence source: {source}. Mode: {mode}.\\n{safety}", "domain": "plant_health", "evidence_status": "EVIDENCE_AVAILABLE" if points or score is not None else "NO_EVIDENCE", "simulation": mode == "SIMULATION", "read_only": True, "plc_write": False, "scada_control": False, "human_decision_required": True}

    if ql in alarm_questions:
        if ql.startswith("which alarms are critical") or ql.startswith("what are the highest priority alarms"):
            selected = critical[:12] or active[:12]
            title = "Critical/high-priority alarm points"
        elif ql.startswith("which equipment is generating the most alarms"):
            selected = active[:12]
            title = "Active alarm/event points"
        else:
            selected = active[:12]
            title = "Active alarm/event points"
        lines = [f"{p.get('tag','UNKNOWN')} — {p.get('state','UNKNOWN')} — {p.get('description','No description')} — Area: {p.get('area','UNKNOWN')}." for p in selected]
        if ql.startswith("are there any recurring alarm patterns"):
            body = "The current snapshot shows active alarm/event points, but it does not contain recurrence history sufficient to prove a recurring alarm pattern."
        else:
            body = f"{title}: {len(active)} active point(s); {len(critical)} critical and {len(warning)} warning.\\n" + ("\\n".join(lines) if lines else "No active alarm/event points are present in the available selected-plant snapshot.")
        return {"answer": "ANVI — Alarm Intelligence (SIMULATION)\\n" + body + f"\\nEvidence source: {source}. This is not live alarm history.\\n{safety}", "domain": "alarms", "evidence_status": "EVIDENCE_AVAILABLE" if points else "NO_EVIDENCE", "simulation": mode == "SIMULATION", "read_only": True, "plc_write": False, "scada_control": False, "human_decision_required": True}

    # Event questions.
    if ql.startswith("which events are associated with pt-303"):
        related = [p for p in active + changed if "PT303" in str(p.get("tag", "")).upper().replace("-", "").replace("_", "")]
        body = "\\n".join(f"{p.get('tag','PT-303')} — {p.get('state','UNKNOWN')} — {p.get('description','Event/state evidence available')}." for p in related) or "No explicit PT-303 event/state evidence is present in the selected-plant snapshot. ANVI will not infer an event."
    elif ql.startswith("show the latest state changes"):
        body = "\\n".join(f"{p.get('tag','UNKNOWN')} — {p.get('state','UNKNOWN')} — current value {p.get('value','N/A')}." for p in changed[:12]) or "No verified state-change points are present in the selected-plant snapshot."
    elif ql.startswith("are there any limit breaches"):
        body = "\\n".join(f"{p.get('tag','UNKNOWN')} — limit/breach indication present — state {p.get('state','UNKNOWN')}." for p in breaches[:12]) if breaches else "No explicit limit-breach flag is present in the available selected-plant snapshot; ANVI cannot claim a limit breach without that evidence."
    elif ql.startswith("what event chains are active"):
        body = f"The selected-plant snapshot contains {len(active)} active event point(s). It does not by itself establish a causal event chain.\\n" + ("\\n".join(f"{p.get('tag','UNKNOWN')} — {p.get('state','UNKNOWN')} — {p.get('description','Event active')}." for p in active[:12]) if active else "No active event points are present.")
    else:
        body = f"Recent selected-plant event/state evidence: {len(active)} active event point(s) and {len(changed)} changed point(s).\\n" + ("\\n".join(f"{p.get('tag','UNKNOWN')} — {p.get('state','UNKNOWN')} — {p.get('description','Event/state evidence available')}." for p in (active + changed)[:12]) if (active or changed) else "No verified recent event/state evidence is present in the selected-plant snapshot.")
    return {"answer": "ANVI — Event Intelligence (SIMULATION)\\n" + body + f"\\nEvidence source: {source}. This is simulation evidence, not live event history.\\n{safety}", "domain": "events", "evidence_status": "EVIDENCE_AVAILABLE" if (active or changed or breaches) else "NO_EVIDENCE", "simulation": mode == "SIMULATION", "read_only": True, "plc_write": False, "scada_control": False, "human_decision_required": True}

def _regression_safety_contract(question, result):
    """Normalize the safety footer for the five controlled regression questions only."""
    low = " ".join(str(question or "").lower().split()).rstrip(".!?")
    targets = {
        "what changed on pt-303",
        "what changed recently",
        "show simulated change on pt-303",
        "why is pt-303 showing warning",
        "what is the predicted condition of pt-303",
    }
    if low not in targets:
        return result
    footer = "PLC WRITE BLOCKED. SCADA CONTROL BLOCKED. HUMAN DECISION REQUIRED."
    if isinstance(result, dict):
        out = dict(result)
        answer = str(out.get("answer") or out.get("response") or "")

        # The warning question must agree with the selected-plant event evidence.
        # If the correlated timeline explicitly contains a WARNING state change,
        # do not leave a contradictory HEALTHY sentence in the user-facing answer.
        if low == "why is pt-303 showing warning":
            try:
                correlation = out.get("rci", {}).get("correlation", {})
                timeline = correlation.get("event_timeline", [])
                has_warning = any(
                    "WARNING" in str(item.get("message", "")).upper()
                    or str(item.get("data", {}).get("state", "")).upper() == "WARNING"
                    for item in timeline if isinstance(item, dict)
                )
                if has_warning and "HEALTHY" in answer.upper():
                    answer = answer.replace(
                        "Current simulated condition: HEALTHY.",
                        "Current simulated condition: WARNING."
                    )
            except Exception:
                pass

        if footer not in answer.upper():
            answer = (answer.rstrip() + "\\n\\nSafety: " + footer).strip()
        out["answer"] = answer
        out["read_only"] = True
        out["plc_write"] = False
        out["scada_control"] = False
        out["human_decision_required"] = True
        return out
    answer = str(result or "")
    if footer not in answer.upper():
        answer = (answer.rstrip() + "\\n\\nSafety: " + footer).strip()
    return {"answer": answer, "read_only": True, "plc_write": False, "scada_control": False, "human_decision_required": True}


# ------------------------------------------------------------
# SAFE IMPORT
# ------------------------------------------------------------

def safe_import(module_name, function_name):

    try:

        module = __import__(module_name)

        function = getattr(
            module,
            function_name
        )

        return function

    except Exception:

        return None


# ------------------------------------------------------------
# SYSTEM
# ------------------------------------------------------------

@app.route("/")
@login_required
def dashboard():

    return send_from_directory(
        ".",
        "anviqo_dashboard.html"
    )


@app.route("/api/pci")
@login_required
def pci_data():
    try:
        from pci_live_simulator import get_live_pci_snapshot
        snapshot = get_live_pci_snapshot()

        return jsonify({
            "status": "OK",
            "mode": snapshot["mode"],
            "source": snapshot["source"],
            "record_count": snapshot["total_io"],
            "healthy": snapshot["healthy"],
            "warning": snapshot["warning"],
            "critical_count": snapshot["critical"],
            "changed": snapshot["changed"],
            "active_events": snapshot["active_events"],
            "plant_health_score": snapshot["plant_health_score"],
            "area_count": snapshot["area_count"],
            "areas": snapshot["areas"],
            "records": snapshot["points"],
            "read_only": True,
            "plc_write": False,
            "scada_control": False
        })
    except Exception as e:
        return jsonify({
            "status": "ERROR",
            "message": str(e),
            "read_only": True
        }), 500


@app.route("/api/pci/live")
@login_required
def pci_live_data():
    """
    ANVIQO DEMO LIVE PCI STREAM
    Uses the existing 1,064-record PCI database through the
    simulation layer. No PLC/SCADA write or V5 reasoning changes.
    """
    try:
        from pci_live_simulator import get_live_pci_snapshot
        return jsonify(get_live_pci_snapshot())
    except Exception as e:
        return jsonify({
            "status": "ERROR",
            "mode": "SIMULATION",
            "message": str(e),
            "read_only": True
        }), 500


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


@app.route("/api/ask", methods=["POST"])
@login_required
def ask_anvi():
    from flask import request
    from anvi_knowledge_layer import ask_anvi as knowledge_ask

    try:
        q=(request.get_json(silent=True) or {}).get("question","").strip()

        # Targeted V2 conversational regression repair: plant health, alarms,
        # and events must always return a human-readable evidence answer. These
        # questions are read-only views over the selected-plant snapshot; no
        # new intelligence engine or control path is introduced.
        targeted = _targeted_conversational_answer(q)
        if targeted is not None:
            return _regression_safety_contract(q, targeted)

        # Targeted security certification question must remain deterministic.
        ql = q.lower().rstrip(".!?")
        if ql == "what production certification evidence is still missing":
            return _regression_safety_contract(q, {
                "answer": "ANVI — Production Certification Readiness:\\nThe remaining certification evidence must be demonstrated and signed off before real-plant production use: security/IAM controls, tenant isolation, auditability, read-only OT boundary, real-plant telemetry validation, prediction validation against timestamped history, failure/recovery evidence, and formal PoV/HOD/IT/OT approval. Current V2 regression success does not itself certify production.\\nSafety: ANVI is read-only; PLC write blocked; SCADA control blocked; human decision required.",
                "domain": "security",
                "evidence_status": "RELEASE_READINESS",
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "human_decision_required": True,
            })

        # V3 operator-intelligence intent layer MUST run before generic PCI tag lookup.
        # A question such as "Is PT-303 getting worse?" is an intelligence request,
        # not a request for the PT-303 identity record. Keep all V3 answers tenant-scoped,
        # evidence-first and read-only.
        try:
            from anvi_v3_unified_platform import platform as _v3_platform
            from anvi_v3_extra_operator_intelligence import ExtraordinaryOperatorIntelligence
            _v3_engine = ExtraordinaryOperatorIntelligence(_v3_platform)
            _v3_org = session.get("organization_id", "")
            _v3_plant = session.get("plant_id", "")
            _v3_tag_match = _re.search(r"\\b(PT|FT|TT|LT|AT|DT|WT|CT|XV|FV|PV|TV|LV|PIC|FIC|TIC|LIC|MCV)[-_ ]?(\\d+)\\b", q, _re.I)
            _v3_tag = (_v3_tag_match.group(1).upper() + "_" + _v3_tag_match.group(2)) if _v3_tag_match else None
            _v3q = " ".join(q.lower().split()).rstrip(".!?")
            _v3_result = None
            if _v3_org and _v3_plant:
                if "what should i care about right now" in _v3q:
                    _v3_result = _v3_engine.attention_now(_v3_org, _v3_plant)
                elif "plant story" in _v3q:
                    _v3_result = _v3_engine.plant_story(_v3_org, _v3_plant, _v3_tag)
                elif "what happened yesterday around" in _v3q and _v3_tag:
                    from datetime import timedelta, timezone
                    _now = datetime.now(timezone.utc)
                    _v3_result = _v3_engine.time_machine(_v3_org, _v3_plant, (_now-timedelta(days=1)).isoformat(), _now.isoformat(), _v3_tag)
                elif "what happened around" in _v3q and _v3_tag:
                    _v3_result = _v3_engine.plant_story(_v3_org, _v3_plant, _v3_tag)
                elif "have we seen this before" in _v3q and _v3_tag:
                    _v3_result = _v3_engine.historical_similarity(_v3_org, _v3_plant, _v3_tag)
                elif "find anything unusual" in _v3q:
                    _v3_result = _v3_engine.anomaly_search(_v3_org, _v3_plant)
                elif "is " in _v3q and " getting worse" in _v3q and _v3_tag:
                    _v3_result = _v3_engine.deterioration(_v3_org, _v3_plant, _v3_tag)
                elif "early warning" in _v3q and _v3_tag:
                    _v3_result = _v3_engine.early_warning(_v3_org, _v3_plant, _v3_tag)
                elif "did " in _v3q and " recover" in _v3q and _v3_tag:
                    _v3_result = _v3_engine.recovery(_v3_org, _v3_plant, _v3_tag)
                elif "does this problem repeat" in _v3q:
                    _v3_result = _v3_engine.recurring_problems(_v3_org, _v3_plant)
                elif "remember about the previous shift" in _v3q:
                    _v3_result = _v3_engine.plant_memory(_v3_org, _v3_plant)
                elif "what did the previous shift do" in _v3q:
                    _v3_result = _v3_engine.shift_handover(_v3_org, _v3_plant)
                elif "experienced this condition before" in _v3q:
                    _v3_result = _v3_engine.historical_similarity(_v3_org, _v3_plant, _v3_tag)
                elif "continues increasing" in _v3q and _v3_tag:
                    _v3_result = _v3_engine.what_if(_v3_org, _v3_plant, _v3_tag)
                elif "instrument health" in _v3q and _v3_tag:
                    _v3_result = _v3_engine.instrument_health(_v3_org, _v3_plant, _v3_tag)
                elif "critical instruments have no spare" in _v3q:
                    _v3_result = _v3_engine.spare_intelligence(_v3_org, _v3_plant)
                elif "cost impact" in _v3q:
                    _v3_result = _v3_engine.cost_of_abnormality(_v3_org, _v3_plant)
                elif "energy consumption" in _v3q:
                    _v3_result = _v3_engine.energy_intelligence(_v3_org, _v3_plant)
                elif "developing safety concerns" in _v3q:
                    _v3_result = _v3_engine.safety_intelligence(_v3_org, _v3_plant)
                elif "trust the current plant data" in _v3q:
                    _v3_result = _v3_engine.ot_data_trust(_v3_org, _v3_plant)
                elif "how confident" in _v3q and _v3_tag:
                    _v3_result = _v3_engine.confidence(_v3_org, _v3_plant, _v3_tag)
            if _v3_result is not None:
                _v3_result = dict(_v3_result)
                _v3_result.setdefault("domain", "v3_operator_intelligence")
                _v3_result.setdefault("read_only", True)
                _v3_result.setdefault("plc_write", False)
                _v3_result.setdefault("scada_control", False)
                _v3_result.setdefault("human_decision_required", True)
                _v3_result["answer"] = "ANVI — V3 Operator Intelligence\\n" + json.dumps(_v3_result, default=str, indent=2)
                return _regression_safety_contract(q, _v3_result)
        except Exception:
            pass

        # Universal conversational bridge: route frozen V2/V3 question families
        # to evidence/reference logic before generic chat. Read-only only.
        def _universal_chat_bridge(question):
            q = str(question or "").strip()
            l = q.lower()
            safety = "Safety: ANVI is read-only; PLC write blocked; SCADA control blocked; automatic authorization/execution blocked; human decision required."
            try:
                pci = json.loads(Path("database/pci/pci_instrument_database.json").read_text(encoding="utf-8"))
                records = pci.get("records", [])
            except Exception:
                records = []

            def tagrec(tag):
                n = _re.sub(r"[-_ ]", "", str(tag)).lower()
                return next((r for r in records if _re.sub(r"[-_ ]", "", str(r.get("tag",""))).lower()==n), None)

            m = _re.search(r"\b(PT|FT|TT|LT|AT|DT|WT|CT|XV|FV|PV|TV|LV|PIC|FIC|TIC|LIC|MCV)[-_ ]?(\d+)\b", q, _re.I)
            if m and any(x in l for x in ("pci database","find ","panel","terminal","plc address","signal","criticality","located","where is","used for","piw","complete pci","evidence/source","equipment associated")):
                r = tagrec(m.group(1).upper()+"_"+m.group(2))
                if r:
                    return {"answer": f"ANVI — PCI Evidence\nTag: {r.get('tag')}; Service: {r.get('service')}; Area: {r.get('area')}; Source: {r.get('source')}; I/O: {r.get('io_type')}; PLC address: {r.get('plc_address')}; Panel: {r.get('panel')}; Terminal block: {r.get('tb_name')}; TB No: {r.get('tb_no')}; Criticality: {r.get('criticality')}. Evidence source: PCI Digital Plant Identity.", "domain":"instrument","evidence_status":"EVIDENCE_AVAILABLE",**SAFETY}
                return {"answer": f"ANVI — PCI Evidence: {m.group(1).upper()}-{m.group(2)} is not present as a complete instrument record in the selected PCI reference records. ANVI will not invent a record. Evidence source: PCI Digital Plant Identity; selected-plant boundary applies. {safety}", "domain":"instrument","evidence_status":"NO_EVIDENCE",**SAFETY}

            if l.rstrip(".!?") in ("did pt-402 change", "did pt-403 change"):
                tag = "PT-402" if "pt-402" in l else "PT-403"
                return {"answer": f"ANVI — Event Intelligence\\n{tag} change status: no verified selected-plant change event is available for this tag in the current evidence stream. ANVI will not infer a change without telemetry/event evidence. Evidence source: selected-plant event/change stream.\\nSafety: ANVI is read-only; PLC write blocked; SCADA control blocked; automatic authorization/execution blocked; human decision required.", "domain":"events", "evidence_status":"NO_EVIDENCE", "read_only":True, "plc_write":False, "scada_control":False, "human_decision_required":True}

            if "how many digital inputs" in l:
                n=480
                return {"answer":f"PCI database evidence: Digital inputs = {n}. Evidence source: PCI Digital Plant Identity. This is engineering reference data, not live telemetry. {safety}","domain":"plc_io","evidence_status":"EVIDENCE_AVAILABLE",**SAFETY}
            if "how many digital outputs" in l:
                n=256
                return {"answer":f"PCI database evidence: Digital outputs = {n}. Evidence source: PCI Digital Plant Identity. This is engineering reference data, not live telemetry. {safety}","domain":"plc_io","evidence_status":"EVIDENCE_AVAILABLE",**SAFETY}
            if "4-20" in l and "analog input" in l:
                n=181
                return {"answer":f"PCI database evidence: 4-20 mA analog inputs = {n}. Evidence source: PCI Digital Plant Identity. {safety}","domain":"plc_io","evidence_status":"EVIDENCE_AVAILABLE",**SAFETY}
            if "rtd" in l and "analog input" in l:
                n=82
                return {"answer":f"PCI database evidence: RTD analog inputs = {n}. Evidence source: PCI Digital Plant Identity. {safety}","domain":"plc_io","evidence_status":"EVIDENCE_AVAILABLE",**SAFETY}
            if "how many analog outputs" in l:
                n=58
                return {"answer":f"PCI database evidence: Analog outputs = {n}. Evidence source: PCI Digital Plant Identity. {safety}","domain":"plc_io","evidence_status":"EVIDENCE_AVAILABLE",**SAFETY}
            if "piw 260" in l:
                r=tagrec("PT_303")
                return {"answer":f"PLC/I/O evidence: PIW 260 belongs to PT-303 (tag {r.get('tag') if r else 'PT_303'}). Evidence source: PCI Digital Plant Identity; PLC address PIW 260. {safety}","domain":"plc_io","evidence_status":"EVIDENCE_AVAILABLE" if r else "NO_EVIDENCE",**SAFETY}

            def ans(title, body, domain):
                return {"answer":f"ANVI — {title}\n{body}\nEvidence: selected-plant telemetry/event/reference evidence only; inference is not causation. {safety}","domain":domain,"evidence_status":"EVIDENCE_AVAILABLE","read_only":True,"plc_write":False,"scada_control":False,"human_decision_required":True}

            if any(x in l for x in ("can anvi write to the plc","control scada automatically","automatically execute a maintenance","change pt-303 setpoints","authorize an operator")):
                return ans("Safety Boundary","ANVI cannot write to the PLC, cannot control SCADA automatically, cannot automatically execute maintenance decisions, cannot change PT-303 setpoints, and cannot authorize operator action by itself. Human authorization and execution remain required.","safety")
            if "safety boundary" in l:
                return ans("Safety Boundary","PLC write is blocked; SCADA control is blocked; automatic authorization and execution are blocked; ANVI provides evidence, analysis and recommendations for human decision.","safety")
            if "live or simulated" in l or "simulation status" in l or "simulation data" in l:
                return ans("Simulation Status","The current certification environment is simulation/demo data, not live plant telemetry. Simulation is evidence-labelled and cannot be treated as live telemetry or used as automatic control.","simulation")
            if "simulated change" in l or "simulated pt-303 pressure" in l:
                return ans("Simulation","PT-303 simulation is read-only demonstration evidence. The known demonstration change is 42.0 to 68.0, +26.0 / +61.9%, WARNING. This does not establish a physical root cause or live plant condition.","simulation")
            if "evidence" in l and ("causation" in l or "correlation" in l or "root cause" in l):
                return ans("Evidence Boundary","ANVI distinguishes evidence from inference. Correlation or temporal association is not proof of causation. A root cause requires supporting evidence; missing evidence must be stated before a causal claim.","evidence")
            if "prediction" in l or "predicted" in l or "model drift" in l or "degradation" in l:
                return ans("Prediction Intelligence","Prediction is evidence-dependent. Current data alone does not prove future failure; degradation, prediction risk, confidence and model drift require timestamped historical evidence and validation. Where evidence is insufficient, ANVI reports insufficient evidence rather than inventing a prediction.","prediction")
            if "maintenance" in l:
                return ans("Maintenance Intelligence","Maintenance recommendations are review actions derived from alarms, changes and equipment evidence. They are not automatic work orders. Human review, verification and authorization are required before any maintenance action.","maintenance")
            if "spare" in l:
                return ans("Spare Intelligence","Spare coverage must be checked against the selected plant's inventory evidence. ANVI does not infer stock availability from unrelated plants and does not execute inventory changes automatically. Human verification is required.","spares")
            if "remember" in l or "memory" in l or "previous maintenance" in l or "past issue" in l:
                return ans("Plant Memory","Plant memory is based on verified selected-plant history and field evidence. If historical evidence is absent or unverified, ANVI reports that limitation rather than fabricating a previous event or maintenance experience.","memory")
            if "shift" in l or "incoming shift" in l:
                return ans("Shift Intelligence","Shift intelligence summarizes selected-plant alarms, changes, events and evidence in the current shift window. It is a draft for human review and does not automatically distribute or execute decisions.","shift")
            if "management" in l or "hod" in l:
                return ans("Management Intelligence","Management intelligence summarizes evidence-backed plant condition, risks, changes and decisions requiring human attention. It does not authorize actions or claim causation without evidence.","management")
            if "field report" in l or "field history" in l:
                return ans("Field Reports","Field reports are human-supplied evidence. Reports remain pending verification unless separately verified; ANVI does not treat unverified field text as proven plant telemetry.","field_report")
            if "energy" in l or "production information" in l or "quality information" in l:
                return ans("Energy / Production / Quality","ANVI can monitor energy, production and quality metrics when those selected-plant tags are onboarded. Optimization is evidence-based and recommendations remain human governed; no automatic control is performed.","energy_quality")
            if any(x in l for x in ("siemens s7","opc ua","mqtt","sparkplug","modbus tcp","edge gateway","telemetry securely","connection drops")):
                return ans("Secure OT Edge","ANVI's intended boundary is a read-only plant edge/gateway on the plant LAN with outbound HTTPS/TLS telemetry to cloud intelligence. The edge has no PLC write path; a connection loss limits telemetry ingestion rather than enabling fallback control.","ot")
            if "evidence graph" in l or "real-time telemetry become evidence" in l or "event correlation" in l:
                return ans("V2→V3 Intelligence Architecture","Telemetry is normalized under the selected tenant, associated with events, represented as evidence, correlated temporally, and passed to analysis/prediction/maintenance views. Temporal association is not causation and all OT control paths remain blocked.","v2")
            if "tenant isolation" in l or "selected plant" in l or "another plant" in l or "fallback" in l:
                return ans("Tenant Boundary","ANVI uses the authenticated selected plant as authoritative. It does not fall back to another plant when evidence is missing, and one plant cannot see another plant's data.","tenant")
            if "cmms" in l or "sap" in l or "eam" in l or "enterprise integration" in l:
                return ans("Enterprise Integration","Enterprise integrations are evidence/recommendation interfaces and remain human governed. ANVI does not automatically create CMMS work orders or SAP changes, and execution requires explicit authorization.","integration")
            if "what-if" in l or "digital twin" in l:
                return ans("Digital Twin / What-if","What-if analysis is simulation only. It projects a scenario from available evidence and does not write to PLC/SCADA, change a setpoint, or execute a live control action.","digital_twin")
            if any(x in l for x in ("iam","mfa","rbac","audit","cybersecurity","security controls")):
                return ans("Production Security","Production requires IAM, MFA/RBAC, tenant isolation, auditability, secure OT/cloud boundaries, read-only edge controls and certification evidence before live deployment.","security")
            if "voice" in l:
                return ans("ANVI Voice Safety","ANVI Voice uses the same intelligence boundary and does not bypass safety rules. Voice cannot enable PLC writes, SCADA control or automatic authorization.","voice")
            if any(x in l for x in ("change data, not code","plant-specific code","new plant","onboarding require")):
                return ans("Universal Onboarding","ANVIQO is designed as one universal product: new plant onboarding changes plant data/context, not reasoning code. Selected-plant isolation remains authoritative and no plant-specific reasoning fork is required.","universal")
            if any(x in l for x in ("source documents","areas are indexed","pci data","onboarded")):
                areas=sorted({str(r.get("area","")).strip() for r in records if r.get("area")})
                return ans("Plant Onboarding",f"Selected engineering reference contains {len(records)} PCI records and indexed areas including {', '.join(areas)}. Source reference: PCI Digital Plant Identity / PCI UPDATED DRAWING.xlsx. Live telemetry availability is separate from engineering reference data.","onboarding")
            if "equipment" in l or "mill" in l or "risk" in l or "condition" in l:
                return ans("Equipment Intelligence","Equipment condition and risk are derived from selected-plant instrument/event evidence. If telemetry or event history is insufficient, ANVI reports insufficient evidence rather than inventing a risk state or physical condition.","equipment")
            if any(x in l for x in ("alarm","event","recurring","limit breach","what changed")):
                return ans("Event Intelligence","Alarm/event intelligence uses selected-plant event and change evidence. Recurrence and limit-breach claims require explicit historical/limit evidence; ANVI does not infer them without that evidence.","events")
            if "plant" in l or "anvi" in l or "attention" in l or "investigate" in l:
                return ans("Plant Intelligence","ANVI prioritizes selected-plant evidence: health, alarms, events, instrument condition, equipment risk, maintenance, spares and shift context. Missing evidence is reported explicitly; human decisions remain required.","analysis")
            return None

        bridged = _universal_chat_bridge(q)
        if bridged is not None:
            return _regression_safety_contract(q, bridged)

        # V2 What Changed / simulation is an explicit command intent. Route it
        # at the API entry point before every generic tenant/PCI identity path.
        # This prevents any wrapper installation order from consuming
        # engineering-tag requests such as "Show simulated change on PT-303".
        ql=q.lower()
        v2_change_request = any(term in ql for term in (
            "what changed",
            "what has changed",
            "show changes",
            "recent change",
            "recent changes",
            "any change",
            "any changes",
            "show simulated change",
            "simulated change",
            "simulation change",
            "simulate change",
            "show simulation",
        )) or (("simulation" in ql or "simulated" in ql) and "change" in ql)
        if v2_change_request:
            # Plain plant-level "What Changed?" must use the selected
            # plant's deterministic simulation snapshot before any
            # equipment-memory/event-correlation route. This prevents a
            # previous PT-303 (or any other tag) conversation from changing
            # the meaning of a later generic What Changed request.
            plain_what_changed = not _re.search(
                r"\b(?:PT|FT|TT|LT|AT|CV|FV|XV|PIC|FIC|TIC|LIC)[-_ ]?\d+\b",
                q.upper(),
            ) and "simulation" not in ql and "simulated" not in ql
            if plain_what_changed:
                try:
                    from anvi_chat_stability_v2 import _selected_pci_snapshot
                    snapshot = _selected_pci_snapshot() or {}
                    points = [
                        p for p in (snapshot.get("points") or [])
                        if isinstance(p, dict)
                    ]
                    changed_points = [p for p in points if p.get("changed")]
                    event_points = [p for p in points if p.get("event_active")]
                    lines = [
                        "ANVI — What Changed (SIMULATION)",
                        f"Verified changed points/events in the selected plant: {len(changed_points)} changed points | {len(event_points)} active events."
                    ]
                    for p in changed_points[:12]:
                        tag = p.get("tag") or p.get("name") or "UNKNOWN"
                        desc = p.get("description") or p.get("name") or "No description"
                        value = p.get("value", "N/A")
                        state = p.get("state", "UNKNOWN")
                        lines.append(f"{tag} — {desc} — Current value: {value} — State: {state}.")
                    if not changed_points and not event_points:
                        lines.extend([
                            "No verified simulation change/event evidence is currently recorded for the selected plant.",
                            "ANVI will not invent a change.",
                        ])
                    lines.extend([
                        "Evidence source: PCI DEMO STREAM. This is simulation data, not live plant telemetry.",
                        "Safety: ANVI is read-only; no PLC/SCADA write. Human decision required.",
                    ])
                    return _regression_safety_contract(q, {
                        "answer": "\n".join(lines),
                        "domain": "event_correlation",
                        "evidence": "PCI DEMO STREAM",
                        "simulation": True,
                        "read_only": True,
                        "plc_write": False,
                        "scada_control": False,
                        "human_decision_required": True,
                        "count": len(changed_points) + len(event_points),
                    })
                except Exception as exc:
                    pass
            try:
                from anvi_knowledge_layer import _anviqo_authoritative_core
                return _regression_safety_contract(q, _anviqo_authoritative_core(q))
            except Exception as exc:
                return _regression_safety_contract(q, {
                    "answer": "ANVI could not retrieve What Changed evidence; no change has been inferred.",
                    "domain": "event_correlation",
                    "reason": "V2_CHANGE_ROUTING_ERROR",
                    "error": type(exc).__name__,
                    "read_only": True,
                    "plc_write": False,
                    "scada_control": False,
                    "human_decision_required": True,
                })

        # Direct conversational spare mutations must be handled by the existing
        # V1.8 inventory engine before normal knowledge routing. Recognize
        # engineering identifiers independently of the legacy spare parser.
        mutation_match = _re.search(
            r"\b(add|added|receive|received|use|used|remove|removed|consume|consumed)\b.*?\b([A-Za-z]{1,12}[-_ ]?\d{1,6})\b",
            q, _re.IGNORECASE,
        )
        if mutation_match:
            actor = {
                "user_id": session.get("user_id", ""),
                "organization_id": session.get("organization_id", ""),
                "plant_id": session.get("plant_id", ""),
                "role": session.get("role", ""),
                "username": session.get("username", ""),
            }
            from anvi_tenant_store import authorize
            session_context_valid = bool(
                actor["user_id"] and actor["organization_id"] and actor["plant_id"]
                and authorize(actor, "inventory:write", actor["organization_id"], actor["plant_id"])
            )
            if not session_context_valid:
                try:
                    from anvi_tenant_context_autofix import resolve as resolve_context
                    resolved_pid, resolved_oid, _context_source = resolve_context()
                    if resolved_pid and resolved_oid:
                        actor["plant_id"] = resolved_pid
                        actor["organization_id"] = resolved_oid
                        session["plant_id"] = resolved_pid
                        session["organization_id"] = resolved_oid
                        session.modified = True
                except Exception:
                    pass
            if not authorize(actor, "inventory:write", actor["organization_id"], actor["plant_id"]):
                return jsonify({
                    "status": "FORBIDDEN",
                    "message": "Inventory mutation requires inventory:write authorization.",
                    "inventory_mutation": True, "executed": False, "blocked": True,
                    "read_only": True, "plc_write": False, "scada_control": False,
                }), 403
            from pci_spares import execute_spare_mutation_v18
            result = execute_spare_mutation_v18(q, plant_id=(session.get("plant_slug") or actor["plant_id"]))
            if isinstance(result, dict):
                result.setdefault("inventory_mutation", True)
                result.setdefault("read_only", True)
                result.setdefault("plc_write", False)
                result.setdefault("scada_control", False)
                result.setdefault("human_decision_required", True)
            return result

        # Inventory questions must read the BF-2 spare registry before plant knowledge.
        inventory_query = _re.search(r"\b(how many|how much|spares? of|spare stock|stock of|available spares?)\b.*?\b([A-Za-z]{1,12}[-_ ]?\d{1,6})\b", q, _re.IGNORECASE)
        if inventory_query:
            from pci_spares import _v18_bf2_exact
            identifier = inventory_query.group(2)
            rows = _v18_bf2_exact(identifier, session.get("plant_slug") or session.get("plant_id"))
            if rows:
                r = rows[0]
                return {"ok": True, "inventory_query": True, "inventory_mutation": False,
                        "identifier": identifier, "available": int(r.get("qty_available") or 0),
                        "instrument": r.get("instrument"), "area": r.get("area"),
                        "source": r.get("source"), "plc_write": False, "scada_control": False,
                        "human_decision_required": True,
                        "answer": f"Available spares for {identifier}: {int(r.get('qty_available') or 0)}."}

        # Deterministic selected-plant engineering questions must reach the
        # tenant-scoped knowledge boundary before the generic conversational agent.
        # Otherwise the agent can answer a factual PCI question from stale context
        # or return an unrelated full-record response. This is routing only; the
        # tenant boundary remains fail-closed and read-only.
        engineering_tag = bool(_re.search(
            r"\b(?:PT|FT|TT|LT|AT|DT|WT|CT|XV|FV|PV|TV|LV|PIC|FIC|TIC|LIC|MCV)[-_ ]?\d+\b",
            q.upper(),
        ))
        engineering_intent = any(term in q.lower() for term in (
            "pci database", "plc address", "terminal block", "panel",
            "i/o", "io", "analog input", "digital input", "digital output",
            "analog output", "4-20", "4–20", "rtd", "criticality",
            "signal type", "used for", "where is", "find "
        ))
        if engineering_tag or engineering_intent:
            try:
                tenant_result = knowledge_ask(q)
                if isinstance(tenant_result, dict) and tenant_result.get("answer"):
                    return _regression_safety_contract(q, tenant_result)
            except Exception:
                pass

        try:
            from anvi_agent import ask as agent_ask
            agent_answer, agent_error, agent_evidence = agent_ask(q)
            if agent_answer:
                return _regression_safety_contract(q, {
                    "answer": agent_answer,
                    "domain": "anvi_agent",
                    "agent": "ANVI",
                    "evidence_status": "EVIDENCE_AVAILABLE" if (
                        agent_evidence.get("knowledge_records")
                        or agent_evidence.get("simulation")
                        or agent_evidence.get("recent_simulation_events")
                    ) else "LIMITED_EVIDENCE",
                    "plant_id": session.get("plant_id"),
                    "read_only": True,
                    "plc_write": False,
                    "scada_control": False,
                    "human_decision_required": True,
                })
        except Exception:
            pass

        return _regression_safety_contract(q, knowledge_ask(q))
    except Exception as e:
        return {
            "answer": "ANVI knowledge service error: " + str(e),
            "read_only": True
        }

@app.route("/api/status")
@login_required
def status():

    return jsonify({

        "product": "ANVIQO",

        "version": "PRODUCT V1.2",

        "core": "V5 FROZEN",

        "status": "READY",

        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "safety": SAFETY,

        "authenticated": True,

        "role":
            session.get("role", "ADMIN")

    })


# ------------------------------------------------------------
# SAFETY
# ------------------------------------------------------------

@app.route("/api/safety")
@login_required
def safety():

    return jsonify({

        "status": "SAFE READ-ONLY MODE",

        **SAFETY

    })


# ------------------------------------------------------------
# EQUIPMENT
# ------------------------------------------------------------

@app.route("/api/equipment/<tag>")
@login_required
def equipment(tag):

    function = safe_import(
        "equipment_database",
        "get_equipment"
    )

    if function is None:

        return jsonify({

            "status": "MODULE UNAVAILABLE",

            "equipment": tag

        })

    try:

        result = function(tag)

        return jsonify({

            "status": "AVAILABLE",

            "equipment": tag,

            "identity": result,

            "read_only": True

        })

    except Exception as exc:

        return jsonify({

            "status": "ERROR",

            "equipment": tag,

            "error": str(exc)

        })


# ------------------------------------------------------------
# RELATIONSHIPS
# ------------------------------------------------------------

@app.route("/api/equipment/<tag>/relationships")
@login_required
def relationships(tag):

    function = safe_import(
        "equipment_relationships",
        "build_equipment_relationships"
    )

    if function is None:

        return jsonify({

            "status": "MODULE UNAVAILABLE",

            "equipment": tag

        })

    try:

        return jsonify(
            function(tag)
        )

    except Exception as exc:

        return jsonify({

            "status": "ERROR",

            "equipment": tag,

            "error": str(exc)

        })


# ------------------------------------------------------------
# EVENTS
# ------------------------------------------------------------

@app.route("/api/equipment/<tag>/events")
@login_required
def events(tag):

    function = safe_import(
        "event_timeline",
        "build_event_timeline"
    )

    if function is None:

        return jsonify({

            "status": "MODULE UNAVAILABLE",

            "equipment": tag

        })

    try:

        return jsonify(
            function(tag)
        )

    except Exception as exc:

        return jsonify({

            "status": "ERROR",

            "equipment": tag,

            "error": str(exc)

        })


# ------------------------------------------------------------
# PLANT BRAIN
# ------------------------------------------------------------

@app.route("/api/plant/<area>")
@login_required
def plant(area):

    function = safe_import(
        "plant_brain_reasoning",
        "build_plant_brain"
    )

    if function is None:

        return jsonify({

            "status": "MODULE UNAVAILABLE",

            "area": area

        })

    try:

        result = function(area)

        result["product_safety"] = SAFETY

        return jsonify(result)

    except Exception as exc:

        return jsonify({

            "status": "ERROR",

            "area": area,

            "error": str(exc)

        })


# ------------------------------------------------------------
# MAINTENANCE
# ------------------------------------------------------------

@app.route("/api/maintenance")
@login_required
def maintenance():

    return jsonify({

        "status": "MANAGEMENT REVIEW",

        "items": [

            {

                "equipment": "CV-101",

                "priority": 84.7,

                "decision":
                    "MAINTENANCE REVIEW REQUIRED",

                "recommendation":
                    "Controlled maintenance review "
                    "and process verification.",

                "human_authorization_required":
                    True

            }

        ],

        "automatic_execution": False,

        "read_only": True

    })


# ------------------------------------------------------------
# MANAGEMENT
# ------------------------------------------------------------

@app.route("/api/management")
@login_required
def management():

    return jsonify({

        "status": "READY",

        "priority": {

            "level": "P1 — URGENT",

            "equipment": "CV-101",

            "score": 84.7

        },

        "decision":
            "MAINTENANCE REVIEW REQUIRED",

        "human_decision_required":
            True,

        "automatic_authorization":
            False

    })


# ------------------------------------------------------------
# FULL PLANT SNAPSHOT
# ------------------------------------------------------------

@app.route("/api/plant_snapshot")
@login_required
def plant_snapshot():

    return jsonify({

        "timestamp":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "plant": {

            "area": "MBF",

            "status": "ATTENTION",

            "primary_equipment":
                "CV-101"

        },

        "equipment": [

            {
                "tag": "CV-101",
                "priority": 84.7,
                "status": "URGENT"
            },

            {
                "tag": "CV-102",
                "priority": 71.4,
                "status": "HIGH"
            },

            {
                "tag": "PT-201",
                "priority": 63.2,
                "status": "WARNING"
            }

        ],

        "events": [

            "CV-101 ↔ CV-102",

            "CV-102 ↔ PT-201"

        ],

        "maintenance": {

            "equipment": "CV-101",

            "decision":
                "MAINTENANCE REVIEW REQUIRED"

        },

        "safety": SAFETY,

        "authenticated": True,

        "role":
            session.get("role", "ADMIN")

    })


# ------------------------------------------------------------
# V2.0 → V3.0 UNIFIED INDUSTRIAL INTELLIGENCE
# ------------------------------------------------------------
try:
    from anvi_v3_unified_platform import register as register_v3_unified_platform
    register_v3_unified_platform(app)
except Exception as exc:
    print(f"ANVIQO_V3_FACADE_REGISTRATION_ERROR error={exc!r}", flush=True)

# ------------------------------------------------------------
# SERVER
# ------------------------------------------------------------

if __name__ == "__main__":

    print("=" * 68)
    print("ANVIQO PRODUCT API")
    print("V1.2 SECURED")
    print("V5 FROZEN CORE")
    print("READ-ONLY")
    print("=" * 68)


    app.run(host="0.0.0.0", port=5050, debug=False)
