"""ANVIQO Failure Prediction V1.1 API/conversation bridge.
Loaded by the production entrypoint without modifying frozen V5 intelligence.
"""
from flask import jsonify, request, session

from anviqo_api_phase2 import app
from anvi_tenant_store import authorize


def _actor():
    return {"user_id": session.get("user_id", ""), "organization_id": session.get("organization_id", ""), "plant_id": session.get("plant_id", ""), "role": session.get("role", ""), "username": session.get("username", "")}


def _question(payload):
    return str(payload.get("question") or payload.get("query") or payload.get("message") or payload.get("text") or "").strip()


def _can_read(actor):
    return authorize(actor, "plant:read", actor["organization_id"], actor["plant_id"])


@app.before_request
def failure_prediction_query_bridge():
    if request.path != "/api/ask" or request.method != "POST" or not session.get("authenticated"):
        return None
    payload = request.get_json(silent=True) or {}
    question = _question(payload)
    try:
        from failure_prediction import is_failure_prediction_query, build_failure_prediction
        if not is_failure_prediction_query(question):
            return None
        actor = _actor()
        if not _can_read(actor):
            return jsonify({"status":"FORBIDDEN","message":"plant:read permission is required for Failure Prediction.","read_only":True,"plc_write":False,"scada_control":False}), 403
        result = build_failure_prediction(question)
        return jsonify({"answer": result["prediction"], "domain":"failure_prediction", "failure_prediction":result, "read_only":True, "plc_write":False, "scada_control":False, "human_decision_required":True})
    except Exception:
        return None


@app.route("/api/failure_prediction", methods=["POST"])
def failure_prediction_api():
    if not session.get("authenticated"):
        return jsonify({"status":"UNAUTHORIZED","message":"ANVIQO authentication required"}), 401
    actor = _actor()
    if not _can_read(actor):
        return jsonify({"status":"FORBIDDEN","message":"plant:read permission is required for Failure Prediction.","plc_write":False,"scada_control":False}), 403
    payload = request.get_json(silent=True) or {}
    query = str(payload.get("query") or payload.get("question") or payload.get("message") or "").strip()
    tag = str(payload.get("tag") or "").strip()
    if not query and not tag:
        return jsonify({"status":"BAD_REQUEST","message":"query or equipment tag is required."}), 400
    try:
        from failure_prediction import build_failure_prediction
        return jsonify(build_failure_prediction(query, tag or None))
    except Exception as exc:
        return jsonify({"status":"ERROR","message":str(exc),"plc_write":False,"scada_control":False,"automatic_execution":False,"human_decision_required":True}), 500


@app.route("/api/failure_prediction/observation", methods=["POST"])
def failure_prediction_observation_api():
    """Store one real, provenance-labelled plant observation.

    This endpoint records data only; it never writes to PLC/SCADA. Simulation/demo
    observations are rejected so they cannot silently become prediction history.
    """
    if not session.get("authenticated"):
        return jsonify({"status":"UNAUTHORIZED","message":"ANVIQO authentication required"}), 401
    actor = _actor()
    if not _can_read(actor):
        return jsonify({"status":"FORBIDDEN","message":"plant:read permission is required to store plant observations.","plc_write":False,"scada_control":False}), 403
    payload = request.get_json(silent=True) or {}
    required = ("tag", "value", "source_type", "source", "provenance")
    missing = [key for key in required if payload.get(key) in (None, "")]
    if missing:
        return jsonify({"status":"BAD_REQUEST","message":"Missing required fields: " + ", ".join(missing)}), 400
    try:
        from failure_prediction_history import record_observation
        record = record_observation(
            tag=payload.get("tag"), value=payload.get("value"), timestamp=payload.get("timestamp"),
            source_type=payload.get("source_type"), source=payload.get("source"), unit=payload.get("unit"),
            state=payload.get("state"), area=payload.get("area"), provenance=payload.get("provenance")
        )
        return jsonify({"status":"RECORDED","observation":record,"prediction_history_changed":True,"plc_write":False,"scada_control":False,"automatic_execution":False,"human_decision_required":True})
    except ValueError as exc:
        return jsonify({"status":"BAD_REQUEST","message":str(exc),"prediction_history_changed":False,"plc_write":False,"scada_control":False}), 400
    except Exception as exc:
        return jsonify({"status":"ERROR","message":str(exc),"prediction_history_changed":False,"plc_write":False,"scada_control":False}), 500


@app.route("/api/failure_prediction/history", methods=["POST"])
def failure_prediction_history_api():
    if not session.get("authenticated"):
        return jsonify({"status":"UNAUTHORIZED","message":"ANVIQO authentication required"}), 401
    actor = _actor()
    if not _can_read(actor):
        return jsonify({"status":"FORBIDDEN","message":"plant:read permission is required for Failure Prediction history.","plc_write":False,"scada_control":False}), 403
    payload = request.get_json(silent=True) or {}
    tag = str(payload.get("tag") or "").strip()
    if not tag:
        return jsonify({"status":"BAD_REQUEST","message":"tag is required."}), 400
    try:
        from failure_prediction_history import history_summary
        return jsonify(history_summary(tag))
    except Exception as exc:
        return jsonify({"status":"ERROR","message":str(exc),"plc_write":False,"scada_control":False}), 500
