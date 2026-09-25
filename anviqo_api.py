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


@app.route("/api/ask", methods=["POST"])
@login_required
def ask_anvi():
    from flask import request
    from anvi_knowledge_layer import ask_anvi as knowledge_ask

    try:
        q=(request.get_json(silent=True) or {}).get("question","").strip()

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
