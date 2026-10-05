"""ANVIQO V2 evidence ledger.

A small durable-contract layer for provenance. Storage backends can later be
PostgreSQL/time-series/event-stream implementations; this module only defines
the evidence object and deterministic append validation.
"""
from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
import hashlib, json

from anvi_global_v2_contracts import Evidence, SAFETY

def evidence_id(evidence: Evidence) -> str:
    payload = json.dumps(asdict(evidence), sort_keys=True, default=str, separators=(",", ":"))
    return "EV-" + hashlib.sha256(payload.encode()).hexdigest()[:24]

def appendable(evidence: Evidence, selected_organization_id: str, selected_plant_id: str) -> dict[str, Any]:
    validation = evidence.validate()
    if not validation["valid"]:
        return {"accepted": False, "reason": "INVALID_EVIDENCE", "validation": validation, "safety": dict(SAFETY)}
    if str(evidence.organization_id) != str(selected_organization_id):
        return {"accepted": False, "reason": "FOREIGN_ORGANIZATION_EVIDENCE_BLOCKED", "safety": dict(SAFETY)}
    if str(evidence.plant_id) != str(selected_plant_id):
        return {"accepted": False, "reason": "FOREIGN_PLANT_EVIDENCE_BLOCKED", "safety": dict(SAFETY)}
    try:
        observed = datetime.fromisoformat(evidence.observed_at.replace("Z", "+00:00"))
    except Exception:
        return {"accepted": False, "reason": "INVALID_TIMESTAMP", "safety": dict(SAFETY)}
    if observed.tzinfo is None:
        return {"accepted": False, "reason": "TIMESTAMP_MUST_HAVE_TIMEZONE", "safety": dict(SAFETY)}
    return {
        "accepted": True,
        "evidence_id": evidence_id(evidence),
        "evidence": asdict(evidence),
        "provenance": {
            "source": evidence.source,
            "observed_at": evidence.observed_at,
            "confidence": evidence.confidence,
        },
        "safety": dict(SAFETY),
    }
