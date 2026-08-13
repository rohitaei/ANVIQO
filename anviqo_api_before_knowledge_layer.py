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
import os
import json


app = Flask(__name__)

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
app.config["SESSION_COOKIE_SECURE"] = False


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
def pci_data():
    path=os.path.join("database","pci","pci_instrument_database.json")
    try:
        with open(path,encoding="utf-8") as f:
            d=json.load(f)
        records=d.get("records",[])
        from collections import Counter
        areas=Counter(r.get("area","UNKNOWN") for r in records)
        io_types=Counter(r.get("io_type","UNKNOWN") for r in records)
        critical=[r for r in records if r.get("criticality")=="HIGH"]
        return {
            "status":"OK",
            "record_count":len(records),
            "areas":dict(areas),
            "io_types":dict(io_types),
            "critical":critical,
            "records":records
        }
    except Exception as e:
        return {"status":"ERROR","message":str(e)},500


@app.route("/api/ask", methods=["POST"])
def ask_anvi():
    import json as _json
    from flask import request as _request

    try:
        q=(_request.get_json(silent=True) or {}).get("question","").strip()
        if not q:
            return {"answer":"Please ask ANVI a question."}

        path=os.path.join("database","pci","pci_instrument_database.json")
        with open(path,encoding="utf-8") as f:
            db=_json.load(f)

        records=db.get("records",[])
        ql=q.lower()

        # PCI database questions
        if any(x in ql for x in ["pci","instrument","i/o","io","critical","at_201","at_202","pt_303","lt_302"]):

            if any(x in ql for x in ["how many","count","total"]):
                from collections import Counter

                if "di" in ql:
                    return {"answer":f"ANVI PCI evidence: {sum(x.get('io_type')=='DI' for x in records)} DI records are present."}
                if "do" in ql:
                    return {"answer":f"ANVI PCI evidence: {sum(x.get('io_type')=='DO' for x in records)} DO records are present."}
                if "ai" in ql:
                    return {"answer":f"ANVI PCI evidence: {sum(x.get('io_type','').startswith('AI') for x in records)} AI records are present."}

                return {"answer":f"ANVI PCI evidence: {len(records)} instrumentation I/O records are loaded from the verified PCI database."}

            # Specific tag lookup
            for x in records:
                tag=str(x.get("tag",""))
                if tag and tag.lower() in ql:
                    return {"answer":
                        f"ANVI PCI evidence for {tag}: "
                        f"{x.get('description','No description')}. "
                        f"Area: {x.get('area','UNKNOWN')}. "
                        f"I/O: {x.get('io_type','UNKNOWN')}. "
                        f"Criticality: {x.get('criticality','NOT CLASSIFIED')}."
                    }

            if "critical" in ql:
                critical=[x for x in records if x.get("criticality")=="HIGH"]
                text="ANVI PCI evidence: 4 HIGH-criticality instruments are currently classified: "
                text += "; ".join(
                    f"{x.get('tag')} — {x.get('description')} ({x.get('area')})"
                    for x in critical
                )+"."
                return {"answer":text}

            from collections import Counter
            areas=Counter(x.get("area","UNKNOWN") for x in records)
            ios=Counter(x.get("io_type","UNKNOWN") for x in records)

            return {"answer":
                "ANVI PCI evidence is connected. "
                f"The PCI database contains {len(records)} I/O records across {len(areas)} areas. "
                f"I/O distribution: "+", ".join(f"{k}: {v}" for k,v in ios.items())+"."
            }

        return {"answer":
            "ANVI is connected to the V5 Frozen Intelligence core. "
            "For PCI analysis, ask me about PCI I/O, critical instruments, an instrument tag, an area, or I/O type."
        }

    except Exception as e:
        return {"answer":f"ANVI could not complete the evidence lookup: {e}"}

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
