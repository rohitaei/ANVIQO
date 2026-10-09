"""ANVIQO V4.1 Evidence Trust & Connector Readiness.

Assesses the quality of evidence already supplied to the read-only boundary.
This module does not connect to industrial systems or claim live connectivity.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from anvi_v3_5_to_v4_enterprise import SAFETY, SOURCES

TRUST_POLICY_VERSION = "V4.1"
GOOD_QUALITY = {"GOOD", "GOOD_QUALITY", "VALID"}
BAD_QUALITY = {"BAD", "BAD_QUALITY", "INVALID", "FAILED"}
UNKNOWN_QUALITY = {"UNCERTAIN", "UNKNOWN", "UNVERIFIED", "NOT_AVAILABLE"}

def _parse_time(value: str | None):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None

def assess_evidence_trust(evidence: list[dict[str, Any]], *, now: datetime | None = None,
                          stale_after_seconds: int = 300) -> dict[str, Any]:
    """Explain trust dimensions; do not turn a score into a safety guarantee."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("TIMEZONE_AWARE_NOW_REQUIRED")
    if stale_after_seconds < 0:
        raise ValueError("STALE_THRESHOLD_MUST_BE_NONNEGATIVE")
    total = len(evidence)
    if not total:
        return {"status":"NO_EVIDENCE","evidence_count":0,"trust_score":0,
                "trust_level":"NO_EVIDENCE","dimensions":{"freshness":"NO_EVIDENCE",
                "quality":"NO_EVIDENCE","lineage":"NO_EVIDENCE","source_diversity":"NO_EVIDENCE"},
                "limitations":["No evidence supplied; no operational conclusion is justified."],
                "causation_claimed":False,"safety":dict(SAFETY)}
    times = [_parse_time(x.get("observed_at") or x.get("timestamp")) for x in evidence]
    known_times = [t for t in times if t is not None]
    ages = [max(0.0,(now.astimezone(timezone.utc)-t).total_seconds()) for t in known_times]
    fresh_count = sum(age <= stale_after_seconds for age in ages)
    quality_values = [str(x.get("quality","UNKNOWN")).upper() for x in evidence]
    good = sum(q in GOOD_QUALITY for q in quality_values)
    bad = sum(q in BAD_QUALITY for q in quality_values)
    unknown = total-good-bad
    lineage_count = sum(bool(x.get("lineage")) for x in evidence)
    sources = {str(x.get("source_type") or x.get("source") or "UNKNOWN").upper() for x in evidence}
    freshness_ratio = fresh_count/total
    quality_ratio = max(0.0,(good-bad)/total)
    lineage_ratio = lineage_count/total
    diversity_score = min(1.0,len(sources)/2.0)
    score = round(100*(0.35*freshness_ratio+0.35*quality_ratio+0.20*lineage_ratio+0.10*diversity_score),1)
    if not known_times:
        freshness = "UNKNOWN"
    elif fresh_count == total:
        freshness = "FRESH"
    elif fresh_count == 0:
        freshness = "STALE"
    else:
        freshness = "MIXED"
    quality = "BAD_PRESENT" if bad else ("VERIFIED_GOOD" if good==total else "PARTIAL_OR_UNKNOWN")
    lineage = "COMPLETE" if lineage_count==total else ("PARTIAL" if lineage_count else "MISSING")
    level = "HIGHER_TRUST" if score >= 85 and bad == 0 and lineage_count == total and freshness == "FRESH" else ("MODERATE_TRUST" if score >= 55 else "LOW_TRUST")
    limits=[]
    if not known_times: limits.append("Timestamps missing or invalid; freshness cannot be established.")
    if bad: limits.append("Bad-quality evidence is present.")
    if unknown: limits.append("Some evidence quality is unknown or unverified.")
    if lineage_count < total: limits.append("Evidence lineage is incomplete.")
    if len(sources)<2: limits.append("Evidence is not corroborated by multiple source types.")
    limits.append("Trust score is an evidence-quality indicator, not a probability of correctness or a safety authorization.")
    return {"status":"ASSESSED","evidence_count":total,"trust_score":score,"trust_level":level,
            "dimensions":{"freshness":freshness,"quality":quality,"lineage":lineage,
                          "source_diversity":"MULTIPLE_SOURCE_TYPES" if len(sources)>=2 else "SINGLE_OR_UNKNOWN_SOURCE"},
            "counts":{"fresh":fresh_count,"bad_quality":bad,"unknown_quality":unknown,
                      "lineage_complete":lineage_count,"source_types":len(sources)},
            "stale_after_seconds":stale_after_seconds,"limitations":limits,
            "causation_claimed":False,"safety":dict(SAFETY)}

def connector_readiness(source: dict[str, Any]) -> dict[str, Any]:
    """Report configuration readiness only; never infer live device connectivity."""
    kind = str(source.get("source_type","")).upper()
    if kind not in SOURCES:
        return {"status":"UNSUPPORTED","source_type":kind,"ready":False,
                "missing":["supported source type"],"live_connection_verified":False,"safety":dict(SAFETY)}
    required = ["source_id","organization_id","plant_id"]
    missing = [k for k in required if not str(source.get(k,"")).strip()]
    read_only = source.get("read_only", True) is True
    if not read_only: missing.append("read_only=true")
    if source.get("enabled", True) is not True: missing.append("enabled=true")
    return {"status":"READY_FOR_CONFIGURATION" if not missing else "NOT_READY",
            "source_type":kind,"ready":not missing,"missing":missing,
            "live_connection_verified":False,
            "note":"Configuration readiness only. No protocol handshake or live telemetry is verified by this function.",
            "safety":dict(SAFETY)}

def validate_scope(evidence: list[dict[str, Any]], organization_id: str, plant_id: str):
    """Reject mixed-scope evidence instead of silently falling back."""
    for row in evidence:
        if str(row.get("organization_id","")) != str(organization_id):
            raise PermissionError("TENANT_BOUNDARY_VIOLATION")
        if str(row.get("plant_id","")) != str(plant_id):
            raise PermissionError("PLANT_BOUNDARY_VIOLATION")
    return {"status":"SCOPE_VALID","evidence_count":len(evidence),
            "cross_plant_fallback":False,"safety":dict(SAFETY)}
