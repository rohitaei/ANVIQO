"""Authenticated ANVIQO cloud ingestion for plant-side edge observations.

Edge authentication is separate from browser sessions. Each gateway must be
explicitly mapped to one organization and plant through ANVI_EDGE_GATEWAYS_JSON.
No cross-plant inference or fallback is permitted.
"""

from __future__ import annotations

import hmac
import json
import os
from typing import Any, Dict

from flask import jsonify, request

from anvi_tenant_store import enabled as tenant_store_enabled, record_audit

def _store_observations(identity, observations):
    """Persist received edge evidence in the existing tenant database."""
    from anvi_tenant_store import _connect, _is_sqlite, _placeholder, init_schema
    init_schema()
    p = _placeholder()
    with _connect() as conn:
        cur = conn.cursor()
        if _is_sqlite():
            cur.execute("""CREATE TABLE IF NOT EXISTS anviqo_edge_observations (
                observation_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL,
                gateway_id TEXT NOT NULL, tag TEXT NOT NULL, value TEXT, timestamp TEXT NOT NULL,
                quality TEXT NOT NULL, source TEXT NOT NULL, protocol TEXT NOT NULL,
                received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS anviqo_edge_observations (
                observation_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, plant_id TEXT NOT NULL,
                gateway_id TEXT NOT NULL, tag TEXT NOT NULL, value TEXT, timestamp TEXT NOT NULL,
                quality TEXT NOT NULL, source TEXT NOT NULL, protocol TEXT NOT NULL,
                received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
        import uuid
        inserted = 0
        for item in observations:
            values = (
                "edge_" + uuid.uuid4().hex,
                identity["organization_id"], identity["plant_id"], identity["gateway_id"],
                str(item.get("tag", "")),
                json.dumps(item.get("value"), ensure_ascii=False),
                str(item.get("timestamp", "")),
                str(item.get("quality", "UNKNOWN")),
                str(item.get("source", "SIEMENS_S7")),
                str(item.get("protocol", "SIEMENS_S7")),
            )
            placeholders = ",".join([p] * 10)
            cur.execute(
                f"INSERT INTO anviqo_edge_observations(observation_id,organization_id,plant_id,gateway_id,tag,value,timestamp,quality,source,protocol) VALUES({placeholders})",
                values,
            )
            inserted += 1
        return inserted


def _gateway_registry() -> dict[str, Any]:
    raw = os.getenv("ANVI_EDGE_GATEWAYS_JSON", "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise RuntimeError("ANVI_EDGE_GATEWAYS_JSON is invalid JSON") from exc
    return value if isinstance(value, dict) else {}


def authenticate_gateway(gateway_id: str, token: str) -> dict[str, str] | None:
    gateway_id = str(gateway_id or "").strip()
    token = str(token or "").strip()
    if not gateway_id or not token:
        return None
    entry = _gateway_registry().get(gateway_id)
    if not isinstance(entry, dict):
        return None
    expected = str(entry.get("token", ""))
    if not expected or not hmac.compare_digest(token, expected):
        return None
    plant_id = str(entry.get("plant_id", "")).strip()
    organization_id = str(entry.get("organization_id", "")).strip()
    if not plant_id or not organization_id:
        return None
    return {"gateway_id": gateway_id, "plant_id": plant_id, "organization_id": organization_id}


def ingest_request():
    if not request.is_secure and request.headers.get("X-Forwarded-Proto", "").lower() != "https":
        return jsonify({"status": "FORBIDDEN", "message": "HTTPS is required", "read_only": True}), 403

    gateway_id = request.headers.get("X-ANVIQO-Gateway", "")
    auth = request.headers.get("Authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    identity = authenticate_gateway(gateway_id, token)
    if identity is None:
        return jsonify({"status": "UNAUTHORIZED", "message": "Invalid edge gateway credentials"}), 401

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"status": "BAD_REQUEST", "message": "JSON object required"}), 400

    payload_plant = str(payload.get("plant_id", "")).strip()
    payload_gateway = str(payload.get("gateway_id", "")).strip()
    if payload_plant != identity["plant_id"] or payload_gateway != identity["gateway_id"]:
        return jsonify({"status": "FORBIDDEN", "message": "Gateway plant scope mismatch"}), 403

    observations = payload.get("observations", [])
    if not isinstance(observations, list):
        return jsonify({"status": "BAD_REQUEST", "message": "observations must be a list"}), 400
    if len(observations) > 500:
        return jsonify({"status": "BAD_REQUEST", "message": "maximum 500 observations per request"}), 400

    # Enforce identity on every observation. The cloud never accepts a
    # gateway-authenticated batch that claims another plant.
    normalized = []
    for item in observations:
        if not isinstance(item, dict):
            return jsonify({"status": "BAD_REQUEST", "message": "invalid observation"}), 400
        if str(item.get("plant_id", "")).strip() != identity["plant_id"]:
            return jsonify({"status": "FORBIDDEN", "message": "observation plant scope mismatch"}), 403
        normalized.append(item)

    if not tenant_store_enabled():
        return jsonify({"status": "NOT_CONFIGURED", "message": "tenant persistence is unavailable"}), 503

    actor = {
        "user_id": None,
        "organization_id": identity["organization_id"],
        "plant_id": identity["plant_id"],
    }
    try:
        stored = _store_observations(identity, normalized)
        audit_id = record_audit(
            actor,
            "EDGE_OBSERVATIONS_RECEIVED",
            "EDGE_GATEWAY",
            identity["gateway_id"],
            {"observation_count": len(normalized), "stored": stored, "protocol": "SIEMENS_S7", "read_only": True},
        )
    except Exception:
        return jsonify({"status": "ERROR", "message": "audit persistence failed"}), 503

    # Raw observations are deliberately returned as accepted evidence here.
    # A future evidence-store table can consume the same envelope without
    # changing the edge contract.
    return jsonify({
        "status": "ACCEPTED",
        "accepted": len(normalized),
        "stored": stored,
        "gateway_id": identity["gateway_id"],
        "plant_id": identity["plant_id"],
        "organization_id": identity["organization_id"],
        "audit_id": audit_id,
        "evidence_status": "RECEIVED",
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "human_decision_required": True,
    }), 202
