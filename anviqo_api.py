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


app = Flask(__name__)
# ------------------------------------------------------------
# UNIFIED INDUSTRIAL INTELLIGENCE PLATFORM
# Remaining V2-V5 domains use the frozen evidence/safety foundation.
# ------------------------------------------------------------
from industrial_intelligence_platform import run_industrial_intelligence, SAFETY as INDUSTRIAL_SAFETY


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





@app.route("/api/edge/observations", methods=["POST"])
def edge_observations():
    from anvi_edge_ingest import ingest_request
    return ingest_request()

@app.route("/api/edge/state", methods=["GET"])
@login_required
def edge_state():
    """Return only selected-plant edge evidence; no cross-plant fallback."""
    try:
        from anvi_edge_evidence import state
        tag = request.args.get("tag") or None
        return jsonify(state(session.get("plant_id") or "", session.get("organization_id") or "", tag))
    except Exception as exc:
        return jsonify({"status":"ERROR","message":type(exc).__name__,"scope":"SELECTED_PLANT_ONLY","read_only":True,"plc_write":False,"scada_control":False}), 400

@app.route("/api/industrial-intelligence", methods=["POST"])
@login_required
def industrial_intelligence():
    """Run unified intelligence using authenticated selected-plant evidence."""
    try:
        payload = request.get_json(silent=True) or {}
        pid = session.get("plant_id")
        oid = session.get("organization_id")
        if not pid:
            return jsonify({
                "status": "NO_SELECTED_PLANT",
                "message": "Select a plant before requesting industrial intelligence.",
                "plant_scope": None,
                "organization_scope": oid,
                "safety": INDUSTRIAL_SAFETY,
            }), 400

        if not any(payload.get(k) for k in (
            "alarms","process_values","sensor_samples","reliability_events",
            "events","maintenance","spares","shift","field","health_evidence"
        )):
            try:
                from anvi_chat_stability_v2 import _query_rows
                rows = _query_rows(
                    pid, oid,
                    terms=["alarm","pressure","temperature","flow","level","maintenance","spare"],
                    limit=500,
                )
            except Exception:
                rows = []

            def meta(row, *keys):
                m = row.get("metadata") if isinstance(row, dict) else {}
                if not isinstance(m, dict):
                    return None
                wanted = {
                    str(k).lower().replace("_","").replace("-","").replace(" ","")
                    for k in keys
                }
                for k, v in m.items():
                    nk = str(k).lower().replace("_","").replace("-","").replace(" ","")
                    if nk in wanted and v not in (None, ""):
                        return v
                return None

            evidence = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                tag = row.get("tag") or row.get("external_id") or row.get("name") or meta(
                    row, "instrument_tag","loop_tag","tag_name"
                )
                value = meta(row, "value","process_value","current_value","pv")
                state = meta(row, "state","status","alarm_state","condition")
                evidence.append({
                    "tag": tag,
                    "equipment": tag,
                    "value": value,
                    "state": state,
                    "quality": meta(row, "quality","signal_quality"),
                    "area": row.get("area"),
                    "service": row.get("service") or row.get("name"),
                    "source": row.get("source"),
                    "timestamp": row.get("created_at"),
                })

            payload = dict(payload)
            payload.setdefault("process_values", [x for x in evidence if x.get("value") is not None])
            payload.setdefault("sensor_samples", [x for x in evidence if x.get("value") is not None])
            payload.setdefault("alarms", [
                x for x in evidence
                if str(x.get("state") or "").upper() in ("ACTIVE","WARNING","CRITICAL","ALARM")
            ])
            payload.setdefault("events", evidence)
            payload.setdefault("health_evidence", evidence)
            payload.setdefault("maintenance", [
                x for x in evidence if "maint" in str(x.get("service") or "").lower()
            ])
            payload.setdefault("spares", [
                x for x in evidence if "spare" in str(x.get("service") or "").lower()
            ])
            payload.setdefault("field", [])
            payload.setdefault("gateway_tags", [x for x in evidence if x.get("tag")])
            payload.setdefault("shift", {
                "abnormal_equipment": payload["alarms"],
                "alarms": payload["alarms"],
                "maintenance": payload["maintenance"],
            })
            payload.setdefault("incident_events", payload["events"])

        result = run_industrial_intelligence(payload)
        result["plant_scope"] = pid
        result["organization_scope"] = oid
        result["evidence_source"] = "SELECTED_PLANT_TENANT_KNOWLEDGE"
        return jsonify(result)
    except Exception as exc:
        return jsonify({
            "status":"ERROR",
            "message":str(exc),
            "safety":INDUSTRIAL_SAFETY,
            "plant_scope":session.get("plant_id"),
            "organization_scope":session.get("organization_id"),
        }), 400

@app.route("/api/ask", methods=["POST"])
@login_required
def ask_anvi():
    from flask import request
    from anvi_knowledge_layer import ask_anvi as knowledge_ask

    try:
        q=(request.get_json(silent=True) or {}).get("question","").strip()

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
            try:
                from anvi_knowledge_layer import _anviqo_authoritative_core
                return _anviqo_authoritative_core(q)
            except Exception as exc:
                return {
                    "answer": "ANVI could not retrieve What Changed evidence; no change has been inferred.",
                    "domain": "event_correlation",
                    "reason": "V2_CHANGE_ROUTING_ERROR",
                    "error": type(exc).__name__,
                    "read_only": True,
                    "plc_write": False,
                    "scada_control": False,
                    "human_decision_required": True,
                }

        # Direct conversational spare mutations must be handled by the existing
        # V1.8 inventory engine before normal knowledge routing. Recognize
        # engineering identifiers independently of the legacy spare parser.
        import re as _re
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
        import re as _re
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

        # Data-first routing: the existing tenant boundary is the
        # authoritative conversational path for engineering and inventory
        # questions. Do this before the general ANVI agent so the LLM cannot
        # bypass spare routing or mix a second telemetry source into the answer.
        data_intent = any(x in ql for x in (
            "spare", "spares", "inventory", "stock", "indent",
            "instrument", "pressure", "temperature", "flow", "level",
            "plc", "i/o", "equipment", "alarm", "event", "plant health",
            "health", "shift report", "maintenance", "what changed",
        ))
        if data_intent:
            try:
                from anvi_chat_stability_v2 import _answer as tenant_answer
                routed = tenant_answer(q)
                if isinstance(routed, dict) and (
                    routed.get("evidence_status") in ("EVIDENCE_AVAILABLE", "NO_EVIDENCE")
                    or routed.get("blocked")
                ):
                    return routed
            except Exception:
                pass

        try:
            from anvi_agent import ask as agent_ask
            agent_answer, agent_error, agent_evidence = agent_ask(q)
            if agent_answer:
                return {
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
                }
        except Exception:
            pass

        return knowledge_ask(q)
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
    """Selected-plant maintenance + spare evidence; never a hard-coded demo list."""
    try:
        from anvi_tenant_context_autofix import resolve as resolve_context
        pid, oid, source = resolve_context()
        if not pid:
            return jsonify({"status":"NO PLANT","items":[],"spares":[],"scope":"SELECTED_PLANT_ONLY",**SAFETY})

        # Reuse tenant knowledge as the universal source for onboarded maintenance/spare evidence.
        from anvi_chat_stability_v2 import _query_rows
        rows = _query_rows(pid, oid, terms=["maintenance"], limit=120)
        spare_rows = _query_rows(pid, oid, terms=["spare"], limit=120)

        def meta(row, *keys):
            m=row.get("metadata") if isinstance(row.get("metadata"),dict) else {}
            wanted={str(k).lower().replace("_","").replace(" ","") for k in keys}
            for k,v in m.items():
                nk=str(k).lower().replace("_","").replace(" ","")
                if nk in wanted and v not in (None,""): return v
            return None

        spares=[]
        for row in spare_rows:
            tag=row.get("tag") or row.get("external_id") or row.get("name")
            if not tag: continue
            q=meta(row,"qty_available","qty","available","stock","quantity")
            minimum=meta(row,"minimum_stock","minimum","qty_required","required_quantity")
            try: qn=float(q) if q not in (None,"") else None
            except Exception: qn=None
            try: mn=float(minimum) if minimum not in (None,"") else None
            except Exception: mn=None
            spares.append({"tag":tag,"equipment":row.get("name") or row.get("service"),"area":row.get("area"),"qty_available":qn,"minimum_stock":mn,"source":row.get("source")})

        # The bundled critical-spare workbook is exposed only when the selected plant
        # has an explicit verified PCI dataset binding; it is never a global fallback.
        try:
            from anvi_verified_pci_adapter import is_bound
            if is_bound(pid, oid):
                import pci_spares
                legacy = pci_spares.load_spares()
                for row in legacy:
                    row=dict(row); row["evidence_scope"]="BOUND_PLANT_VERIFIED_PCI"; spares.append(row)
        except Exception:
            pass

        low=[x for x in spares if x.get("qty_available") is not None and x.get("minimum_stock") is not None and x["qty_available"]<=x["minimum_stock"]]
        return jsonify({
            "status":"OK" if (rows or spares) else "NO DATA",
            "scope":"SELECTED_PLANT_ONLY","plant_id":pid,"organization_id":oid,
            "items":[{"equipment":r.get("tag") or r.get("external_id") or r.get("name"),"area":r.get("area"),"source":r.get("source"),"evidence":r.get("content") or r.get("service") or r.get("name")} for r in rows[:50]],
            "spares":spares[:200],"critical_spares":len(spares),"low_stock":len(low),
            "maintenance_items":len(rows),"human_decision_required":True,**SAFETY
        })
    except Exception as exc:
        return jsonify({"status":"ERROR","message":type(exc).__name__,"scope":"SELECTED_PLANT_ONLY",**SAFETY}),400


# ------------------------------------------------------------
# MANAGEMENT
# ------------------------------------------------------------

@app.route("/api/management")
@login_required
def management():
    """Selected-plant management evidence; no synthetic equipment or score."""
    try:
        from anvi_full_intelligence import build_context
        ctx=build_context("management decision current plant situation")
        live=ctx.get("live_observation") or {}
        attention=ctx.get("attention_points") or []
        return jsonify({
            "status":"READY" if ctx.get("sources") else "NO DATA",
            "scope":"SELECTED_PLANT_ONLY",
            "plant":ctx.get("plant"),
            "plant_health_score":live.get("plant_health_score"),
            "attention_points":attention[:20],
            "knowledge_count":len(ctx.get("knowledge") or []),
            "evidence_sources":ctx.get("sources") or [],
            "decision":"HUMAN REVIEW REQUIRED" if attention else "NO VERIFIED PRIORITY IDENTIFIED",
            "human_decision_required":True,
            **SAFETY,
        })
    except Exception as exc:
        return jsonify({"status":"ERROR","message":type(exc).__name__,"scope":"SELECTED_PLANT_ONLY",**SAFETY}),400


# ------------------------------------------------------------
# FULL PLANT SNAPSHOT
# ------------------------------------------------------------

@app.route("/api/plant_snapshot")
@login_required
def plant_snapshot():
    """Universal selected-plant snapshot assembled from existing intelligence."""
    try:
        from anvi_full_intelligence import build_context
        ctx=build_context("current plant situation")
        live=ctx.get("live_observation") or {}
        return jsonify({
            "timestamp":live.get("timestamp"),
            "plant":ctx.get("plant"),
            "live_observation":live,
            "attention_points":(ctx.get("attention_points") or [])[:50],
            "events":(ctx.get("events") or [])[:50],
            "knowledge_count":len(ctx.get("knowledge") or []),
            "evidence_sources":ctx.get("sources") or [],
            "scope":"SELECTED_PLANT_ONLY",
            **SAFETY,
            "authenticated":True,
            "role":session.get("role","ADMIN"),
        })
    except Exception as exc:
        return jsonify({"status":"ERROR","message":type(exc).__name__,"scope":"SELECTED_PLANT_ONLY",**SAFETY}),400


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
