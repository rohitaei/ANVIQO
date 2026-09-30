"""V2 Command Centre stream HTTP adapter."""
from flask import jsonify, request, session

from anviqo_spare_query_guard import app
from v2_command_centre_stream import build_command_centre_stream
from v2_simulation_proof import run_v2_simulation_proof


@app.route("/api/command-centre/stream", methods=["GET"])
def command_centre_stream_api():
    if not session.get("authenticated") or not session.get("plant_id"):
        return jsonify({
            "status": "UNAUTHORIZED",
            "scope": "NONE",
            "events": [],
            "changes": [],
            "evidence_count": 0,
            "message": "ANVIQO authentication and selected plant context required.",
        }), 401

    tag = (request.args.get("tag") or "").strip() or None
    query = (request.args.get("q") or "").strip()
    try:
        return jsonify(build_command_centre_stream(query, tag))
    except Exception as exc:
        return jsonify({
            "status": "INSUFFICIENT_EVIDENCE",
            "scope": "SELECTED_PLANT_ONLY",
            "plant_id": session.get("plant_id"),
            "organization_id": session.get("organization_id"),
            "events": [],
            "changes": [],
            "evidence_count": 0,
            "error_type": type(exc).__name__,
            "safety": {
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "automatic_authorization": False,
                "automatic_execution": False,
                "human_decision_required": True,
            },
        })


@app.route("/api/v2/simulation/proof", methods=["GET", "POST"])
def v2_simulation_proof_api():
    """Deterministic V2 acceptance proof; simulation only, no production writes."""
    if not session.get("authenticated") or not session.get("plant_id"):
        return jsonify({
            "status": "UNAUTHORIZED",
            "scope": "NONE",
            "message": "ANVIQO authentication and selected plant context required.",
        }), 401

    try:
        result = run_v2_simulation_proof()
        result["scope"] = "SELECTED_PLANT_ONLY"
        result["plant_id"] = session.get("plant_id")
        result["organization_id"] = session.get("organization_id")
        return jsonify(result), 200 if result["status"] == "PASS" else 500
    except Exception as exc:
        return jsonify({
            "status": "FAIL",
            "test": "V2.0 REAL-TIME INDUSTRIAL INTELLIGENCE — SIMULATION PROOF",
            "mode": "SIMULATION",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "safety": {
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "automatic_authorization": False,
                "automatic_execution": False,
                "human_decision_required": True,
            },
        }), 500
