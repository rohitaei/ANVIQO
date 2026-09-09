"""ANVIQO Failure Prediction Intelligence V1.
Evidence-gated conditional prediction over existing plant signals and history.
No invented trends, thresholds, probabilities, causation, PLC writes, or SCADA control.
"""
from __future__ import annotations

import importlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

VERSION = "ANVIQO-FP-V1.0"
SAFETY = {
    "control_mode": "READ_ONLY",
    "plc_write": False,
    "scada_control": False,
    "automatic_execution": False,
    "human_decision_required": True,
}
_TAG_RE = re.compile(r"\b(?:PT|FT|LT|TT|DP|MCV|SOV|FSV|PCV|POSR|TCV|FV|XV|CV)\s*[-_ ]?\s*\d{1,5}\b", re.I)


def _load(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def _call(module, function: str, *args, **kwargs):
    if module is None:
        return None
    fn = getattr(module, function, None)
    if not callable(fn):
        return None
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _norm_tag(tag: str) -> str:
    value = str(tag or "").upper().strip()
    match = _TAG_RE.search(value)
    if match:
        value = match.group(0)
    return re.sub(r"[^A-Z0-9]", "", value)


def _variants(tag: str) -> List[str]:
    canonical = re.sub(r"[-_ ]+", "-", str(tag or "").upper().strip())
    match = re.match(r"^([A-Z]+)-?(\d{1,5})$", canonical)
    if not match:
        return [canonical] if canonical else []
    p, n = match.groups()
    return [f"{p}-{n}", f"{p}_{n}", f"{p} {n}", f"{p}{n}"]


def extract_tag(text: str) -> Optional[str]:
    match = _TAG_RE.search(str(text or ""))
    if not match:
        return None
    return re.sub(r"\s*[-_ ]\s*", "-", match.group(0).upper())


def is_failure_prediction_query(query: str) -> bool:
    q = " ".join(str(query or "").strip().lower().split())
    if not q or not _TAG_RE.search(q):
        return False
    prediction_words = ("predict", "prediction", "likely to fail", "future failure", "failure risk", "deteriorate", "deterioration", "will fail", "going to fail")
    return any(word in q for word in prediction_words)


def _pci(tag: str) -> Tuple[Any, Any]:
    module = _load("pci_conversation")
    if module is None:
        return None, None
    identity = None
    for variant in _variants(tag):
        identity = _call(module, "find_tag", variant)
        if identity is not None:
            break
    live = None
    snapshot = _call(module, "get_live_pci_snapshot")
    wanted = _norm_tag(tag)
    if isinstance(snapshot, dict):
        for point in snapshot.get("points", []) if isinstance(snapshot.get("points"), list) else []:
            if isinstance(point, dict) and _norm_tag(point.get("tag")) == wanted:
                live = point
                break
    return identity, live


def _memory(tag: str) -> List[Dict[str, Any]]:
    records = _call(_load("plant_memory"), "search_all_memory", query="", limit=1000)
    if not isinstance(records, list):
        return []
    wanted = _norm_tag(tag)
    out = []
    for record in records:
        if not isinstance(record, dict) or _norm_tag(record.get("tag")) != wanted:
            continue
        verified = record.get("verified") is True or str(record.get("verification_status", "")).upper() == "VERIFIED" or record.get("human_verified") is True
        if verified and record.get("source") == "technician field report":
            out.append(record)
    return out


def _events(tag: str) -> List[Dict[str, Any]]:
    module = _load("event_timeline")
    out: List[Dict[str, Any]] = []
    if module is None:
        return out
    seen = set()
    for variant in _variants(tag):
        rows = _call(module, "get_events", variant)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                key = (row.get("timestamp"), row.get("event_type"), row.get("message"))
                if key not in seen:
                    seen.add(key)
                    out.append(row)
    out.sort(key=lambda x: str(x.get("timestamp") or ""))
    return out


def _health(tag: str):
    module = _load("equipment_health")
    for variant in _variants(tag):
        value = _call(module, "get_latest_health", variant)
        if value is not None:
            return value
    return None


def _numeric_history(memory: List[Dict[str, Any]], events: List[Dict[str, Any]], live: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only explicitly timestamped numeric observations; never synthesize points."""
    observations: List[Dict[str, Any]] = []
    for source, rows in (("VERIFIED_PLANT_MEMORY", memory), ("EVENT_TIMELINE", events)):
        for row in rows:
            timestamp = row.get("timestamp")
            if timestamp is None:
                continue
            candidates = []
            for key in ("value", "process_value", "reading", "measurement"):
                if key in row:
                    candidates.append((key, row.get(key)))
            data = row.get("data")
            if isinstance(data, dict):
                for key in ("value", "process_value", "reading", "measurement"):
                    if key in data:
                        candidates.append((key, data.get(key)))
            for key, raw in candidates:
                try:
                    number = float(raw)
                except (TypeError, ValueError):
                    continue
                observations.append({"source": source, "timestamp": timestamp, "value": number, "field": key})
    if isinstance(live, dict) and live.get("value") is not None:
        # The live point is a current observation only. It is not treated as historical trend data.
        observations.append({"source": str(live.get("source") or "PCI_LIVE"), "timestamp": live.get("timestamp"), "value": float(live.get("value")), "field": "value", "current": True})
    observations.sort(key=lambda x: str(x.get("timestamp") or ""))
    return observations


def _trend(observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    historical = [x for x in observations if x.get("timestamp") and not x.get("current")]
    if len(historical) < 2:
        return {"status": "UNAVAILABLE", "reason": "At least two timestamped historical numeric observations are required; no trend is inferred from a single live value.", "observations_used": len(historical)}
    first, last = historical[0], historical[-1]
    delta = last["value"] - first["value"]
    direction = "RISING" if delta > 0 else "FALLING" if delta < 0 else "STABLE"
    return {"status": "AVAILABLE", "direction": direction, "delta": delta, "first": first, "last": last, "observations_used": len(historical)}


def build_failure_prediction(query: str, tag: Optional[str] = None) -> Dict[str, Any]:
    query = str(query or "").strip()
    tag = extract_tag(tag or query) or str(tag or "").strip().upper()
    identity, live = _pci(tag) if tag else (None, None)
    memory = _memory(tag) if tag else []
    events = _events(tag) if tag else []
    health = _health(tag) if tag else None
    observations = _numeric_history(memory, events, live)
    trend = _trend(observations)

    evidence_basis: List[str] = []
    if live is not None:
        evidence_basis.append("Current PCI live observation is available.")
    if identity is not None:
        evidence_basis.append("Authoritative PCI equipment identity is available.")
    if memory:
        evidence_basis.append(f"{len(memory)} verified field-report record(s) are available.")
    if events:
        evidence_basis.append(f"{len(events)} Event Timeline record(s) are available.")
    if health is not None:
        evidence_basis.append("Current equipment-health context is available.")
    if trend["status"] == "AVAILABLE":
        evidence_basis.append("A timestamped historical numeric trend is available from stored evidence.")

    risk_signal = "UNAVAILABLE"
    prediction = "Prediction unavailable: insufficient historical evidence to establish a deterioration trend."
    confidence = "INSUFFICIENT_EVIDENCE"
    reasoning = "ANVIQO will not infer a future failure from a single live value, an event_active flag, a risk score, or an assumed threshold."
    status = "INSUFFICIENT_EVIDENCE"

    if trend["status"] == "AVAILABLE":
        direction = trend["direction"]
        if direction == "RISING":
            risk_signal = "TREND_RISING"
            prediction = "A continued rise in the observed parameter is possible if the documented trend persists. This is a conditional prediction, not a confirmed future failure."
            confidence = "EVIDENCE_BACKED"
            reasoning = "The prediction is based only on the direction calculated from timestamped historical numeric observations; no probability or failure date is invented."
            status = "PREDICTION_AVAILABLE"
        elif direction == "FALLING":
            risk_signal = "TREND_FALLING"
            prediction = "A continued fall in the observed parameter is possible if the documented trend persists. This is a conditional prediction, not a confirmed future failure."
            confidence = "EVIDENCE_BACKED"
            reasoning = "The prediction is based only on the direction calculated from timestamped historical numeric observations; no probability or failure date is invented."
            status = "PREDICTION_AVAILABLE"
        else:
            risk_signal = "TREND_STABLE"
            prediction = "No deterioration direction is established by the available timestamped observations."
            confidence = "EVIDENCE_BACKED"
            reasoning = "The available historical observations do not show a numeric change between the earliest and latest stored points."
            status = "NO_DETERIORATION_SIGNAL"

    return {
        "prediction_version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "tag": tag,
        "status": status,
        "risk_signal": risk_signal,
        "prediction": prediction,
        "confidence": confidence,
        "reasoning": reasoning,
        "trend": trend,
        "observed_condition": {
            "state": live.get("state") if isinstance(live, dict) else None,
            "value": live.get("value") if isinstance(live, dict) else None,
            "changed": live.get("changed") if isinstance(live, dict) else None,
            "event_active": live.get("event_active") if isinstance(live, dict) else None,
            "mode": live.get("mode") if isinstance(live, dict) else None,
            "source": live.get("source") if isinstance(live, dict) else None,
        },
        "evidence_summary": {
            "pci_identity_available": identity is not None,
            "live_available": live is not None,
            "verified_memory_count": len(memory),
            "event_count": len(events),
            "health_available": health is not None,
            "numeric_observation_count": len(observations),
            "evidence_basis": evidence_basis,
        },
        "evidence": {
            "pci_identity": identity,
            "pci_live": live,
            "verified_plant_memory": memory,
            "event_timeline": events,
            "equipment_health": health,
            "numeric_observations": observations,
        },
        "safety": dict(SAFETY),
        "decision_status": "HUMAN_DECISION_REQUIRED",
    }
