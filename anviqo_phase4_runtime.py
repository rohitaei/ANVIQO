"""Production wrapper for the ANVIQO Phase 4 read-only intelligence layer."""
from __future__ import annotations

from flask import jsonify, request

from anviqo_spare_query_guard import app
from phase4_advanced_intelligence import build_phase4_snapshot


@app.route("/api/phase4", methods=["GET", "POST"])
def phase4():
    """Return Phase 4 evidence-backed intelligence.

    GET returns the contract with insufficient-evidence states because this
    endpoint never invents energy, production or safety measurements.
    POST accepts an evidence object supplied by an existing ANVIQO data layer.
    """
    if not request.path.startswith("/api/phase4"):
        return None
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        evidence = payload.get("evidence", payload)
        if not isinstance(evidence, dict):
            return jsonify({"status": "ERROR", "message": "evidence must be an object", "read_only": True}), 400
    else:
        evidence = {}
    result = build_phase4_snapshot(evidence)
    result["source"] = "ANVIQO Phase 4 evidence contract"
    return jsonify(result)
