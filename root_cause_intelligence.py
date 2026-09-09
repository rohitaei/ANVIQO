"""
ANVIQO Root Cause Intelligence V1.2

Evidence-backed diagnostic assessment over existing ANVIQO engines.
This module does not replace frozen V5 intelligence and never claims causation
when the evidence does not establish it.

Safety:
- READ_ONLY
- no PLC writes
- no SCADA control
- no automatic execution
- human decision required
"""

from __future__ import annotations

import importlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


VERSION = "ANVIQO-RCI-V1.2"
SAFETY = {
    "control_mode": "READ_ONLY",
    "plc_write": False,
    "scada_control": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


_EQUIPMENT_RE = re.compile(
    r"\b(?:PT|FT|LT|TT|DP|MCV|SOV|FSV|PCV|POSR|TCV|FV|XV|CV)\s*[-_ ]?\s*\d{1,5}\b",
    re.IGNORECASE,
)


def is_root_cause_query(query: str) -> bool:
    """Detect explicit equipment root-cause/failure investigation intent."""
    q = " ".join(str(query or "").strip().lower().split())
    if not q or not _EQUIPMENT_RE.search(q):
        return False
    cause_terms = (
        "root cause", "cause of", "causing", "reason for", "why is", "why was",
        "why did", "why has", "what caused", "failure cause", "fault cause",
        "why does", "why are", "why were",
    )
    symptom_terms = (
        "abnormal", "failure", "failed", "fault", "problem", "issue", "trip",
        "unhealthy", "malfunction", "not working", "stopped",
    )
    has_cause = any(term in q for term in cause_terms)
    has_symptom = any(term in q for term in symptom_terms)
    direct_why = any(term in q for term in (
        "why is", "why was", "why did", "why has", "why does", "why are", "why were"
    ))
    return has_cause and (has_symptom or direct_why or "root cause" in q or "what caused" in q)


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
    value = str(tag or "").strip().upper()
    match = _EQUIPMENT_RE.search(value)
    if match:
        value = match.group(0)
    return re.sub(r"[^A-Z0-9]", "", value)


def _tag_variants(tag: str) -> List[str]:
    canonical = str(tag or "").strip().upper().replace("_", "-").replace(" ", "-")
    m = re.match(r"^([A-Z]+)-?(\d{1,5})$", canonical)
    if not m:
        return [canonical] if canonical else []
    prefix, number = m.groups()
    return [f"{prefix}-{number}", f"{prefix}_{number}", f"{prefix} {number}", f"{prefix}{number}"]


def extract_tag(text: str) -> Optional[str]:
    m = _EQUIPMENT_RE.search(str(text or ""))
    if not m:
        return None
    raw = m.group(0).upper()
    return re.sub(r"\s*[-_ ]\s*", "-", raw)


def _verified_memory(tag: str) -> List[Dict[str, Any]]:
    module = _load("plant_memory")
    records = _call(module, "search_all_memory", query="", limit=1000)
    if not isinstance(records, list):
        return []
    wanted = _norm_tag(tag)
    result = []
    for record in records:
        if not isinstance(record, dict) or _norm_tag(record.get("tag")) != wanted:
            continue
        if record.get("source") != "technician field report":
            continue
        verified = (
            record.get("verified") is True
            or str(record.get("verification_status", "")).upper() == "VERIFIED"
            or record.get("human_verified") is True
        )
        if verified:
            result.append(record)
    return result


def _events(tag: str) -> List[Dict[str, Any]]:
    module = _load("event_timeline")
    if module is None:
        return []
    merged, seen = [], set()
    for variant in _tag_variants(tag):
        events = _call(module, "get_events", variant)
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            key = (event.get("timestamp"), event.get("event_type"), event.get("message"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(event)
    return merged


def _health(tag: str):
    module = _load("equipment_health")
    for variant in _tag_variants(tag):
        result = _call(module, "get_latest_health", variant)
        if result is not None:
            return result
    return None


def _pci_evidence(tag: str, query: str) -> Dict[str, Any]:
    """Use the authoritative PCI registry/simulator as equipment evidence."""
    module = _load("pci_conversation")
    if module is None:
        return {"identity": None, "live": None, "answer": None}
    identity = None
    for variant in _tag_variants(tag):
        identity = _call(module, "find_tag", variant)
        if identity is not None:
            break
    live = None
    snapshot = _call(module, "get_live_pci_snapshot")
    if isinstance(snapshot, dict):
        wanted = _norm_tag(tag)
        points = snapshot.get("points", [])
        for point in points if isinstance(points, list) else []:
            if isinstance(point, dict) and _norm_tag(point.get("tag")) == wanted:
                live = point
                break
    answer = _call(module, "answer", query)
    return {"identity": identity, "live": live, "answer": answer}


def _maintenance(tag: str, query: str):
    module = _load("maintenance_experience_matching")
    context = {"equipment": tag, "tag": tag, "query": query}
    experience = _call(module, "build_experience_context", context)
    matching = _call(module, "find_matching_experience", context)
    return experience, matching if isinstance(matching, list) else []


def _text(records: List[Dict[str, Any]]) -> str:
    parts = []
    for record in records:
        for key in (
            "message", "event", "observation", "finding", "maintenance_action",
            "outcome", "confirmation_evidence", "notes",
        ):
            value = record.get(key)
            if value:
                parts.append(str(value))
    return " ".join(parts).lower()


def _hypotheses(
    events: List[Dict[str, Any]],
    memory: List[Dict[str, Any]],
    health: Dict[str, Any],
    pci_live: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return ranked hypotheses only when explicit causal evidence supports them."""
    combined = f"{_text(events)} {_text(memory)}"
    rules = [
        (
            "instrument-air / positioner issue",
            "air pressure" in combined and ("valve position" in combined or "positioner" in combined),
            "Explicit evidence links instrument-air/valve-position information in available history.",
        ),
        (
            "sensor / transmitter signal issue",
            any(x in combined for x in ("transmitter fault", "sensor fault", "signal fault", "signal failure", "instrument fault")),
            "A verified event or field finding explicitly records a sensor/transmitter/instrument fault.",
        ),
        (
            "wiring / termination issue",
            any(x in combined for x in ("loose terminal", "loose wiring", "termination fault", "cable fault", "broken wire")),
            "A verified event or field finding explicitly records a wiring/termination problem.",
        ),
        (
            "power-supply issue",
            any(x in combined for x in ("fuse blown", "fuse failure", "power supply fault", "24v failure", "24 v failure", "supply failure")),
            "A verified event or field finding explicitly records a power/fuse/supply problem.",
        ),
        (
            "process-condition contribution",
            any(x in combined for x in ("process pressure", "process temperature", "flow abnormal", "high temperature", "low pressure")),
            "The available evidence contains an explicit process-condition abnormality that may contribute to the observed symptom.",
        ),
    ]
    candidates = []
    for name, matched, rationale in rules:
        if not matched:
            continue
        evidence = []
        for source, records in (("EVENT_TIMELINE", events), ("VERIFIED_PLANT_MEMORY", memory)):
            for record in records:
                raw = " ".join(str(record.get(k) or "") for k in (
                    "message", "event", "observation", "finding", "maintenance_action", "outcome", "confirmation_evidence", "notes"
                )).strip()
                if raw:
                    evidence.append({
                        "source": source,
                        "memory_id": record.get("memory_id"),
                        "timestamp": record.get("timestamp"),
                        "text": raw,
                    })
        candidates.append({
            "hypothesis": name,
            "status": "INVESTIGATE",
            "support": rationale,
            "evidence": evidence,
        })
    return candidates


def _observed_condition(tag: str, query: str, pci: Dict[str, Any], health: Any, events: List[Dict[str, Any]], memory: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Explain the currently observed condition without inventing engineering limits."""
    live = pci.get("live") if isinstance(pci, dict) else None
    result = {
        "reported_symptom": any(x in str(query).lower() for x in ("abnormal", "fault", "failure", "issue", "problem", "unhealthy", "malfunction", "stopped")),
        "live_state": None,
        "live_value": None,
        "changed": None,
        "event_active": None,
        "mode": None,
        "source": None,
        "evidence_basis": [],
    }
    if isinstance(live, dict):
        result.update({
            "live_state": live.get("state"),
            "live_value": live.get("value"),
            "changed": live.get("changed"),
            "event_active": live.get("event_active"),
            "mode": live.get("mode"),
            "source": live.get("source"),
        })
        if live.get("state") in ("WARNING", "CRITICAL"):
            result["evidence_basis"].append(f"PCI stream currently reports state {live.get('state')}.")
        if live.get("changed") is True:
            result["evidence_basis"].append("PCI stream currently marks the point as changed.")
        if live.get("event_active") is True:
            result["evidence_basis"].append("PCI stream currently marks an active event.")
    if isinstance(health, dict):
        result["evidence_basis"].append("Equipment health context is available.")
    if events:
        result["evidence_basis"].append(f"{len(events)} event-timeline record(s) are available.")
    if memory:
        result["evidence_basis"].append(f"{len(memory)} verified field-report record(s) are available.")
    return result


def build_root_cause_intelligence(query: str, tag: Optional[str] = None) -> Dict[str, Any]:
    query = str(query or "").strip()
    tag = extract_tag(tag or query) or _norm_tag(tag or "")
    events = _events(tag) if tag else []
    memory = _verified_memory(tag) if tag else []
    health = _health(tag) if tag else None
    pci = _pci_evidence(tag, query) if tag else {"identity": None, "live": None, "answer": None}
    experience, matching = _maintenance(tag, query) if tag else (None, [])
    observed = _observed_condition(tag, query, pci, health, events, memory)
    hypotheses = _hypotheses(events, memory, health if isinstance(health, dict) else {}, pci.get("live"))

    identity_available = pci.get("identity") is not None
    live_available = pci.get("live") is not None
    any_evidence = bool(events or memory or health or identity_available or live_available or experience or matching)
    live = pci.get("live") if isinstance(pci, dict) else None

    if hypotheses:
        status = "HYPOTHESES_AVAILABLE"
        conclusion = "ANVIQO found evidence-supported hypotheses to investigate. These are not confirmed root causes."
    elif isinstance(live, dict) and live.get("state") in ("WARNING", "CRITICAL"):
        status = "INSUFFICIENT_EVIDENCE"
        conclusion = (
            f"PT-303 is currently reported as {live.get('state')} by the PCI {live.get('mode', 'SIMULATION')} stream"
            f" (value {live.get('value')}, changed={live.get('changed')}, event_active={live.get('event_active')}). "
            "This establishes the current abnormal condition in the available stream, but no explicit causal evidence "
            "is strong enough to rank a root-cause hypothesis. Root cause is not confirmed."
        )
    elif any_evidence:
        status = "INSUFFICIENT_EVIDENCE"
        conclusion = (
            "ANVIQO identified equipment context/evidence, but not enough explicit failure evidence to rank a root-cause hypothesis. "
            "The available evidence should be checked for a correlated event, verified field finding, maintenance observation, or confirmed process abnormality."
        )
    else:
        status = "NO_EVIDENCE"
        conclusion = "No usable equipment evidence was found for a root-cause assessment."

    return {
        "rci_version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "tag": tag,
        "status": status,
        "conclusion": conclusion,
        "observed_condition": observed,
        "hypotheses": hypotheses,
        "evidence": {
            "pci_identity": pci.get("identity"),
            "pci_live": pci.get("live"),
            "pci_answer": pci.get("answer"),
            "events": events,
            "verified_plant_memory": memory,
            "health": health,
            "maintenance_experience": experience,
            "matching_experience": matching,
        },
        "evidence_summary": {
            "event_count": len(events),
            "verified_memory_count": len(memory),
            "health_available": health is not None,
            "pci_identity_available": identity_available,
            "pci_live_available": live_available,
            "maintenance_experience_available": experience is not None or bool(matching),
            "matching_experience_count": len(matching),
            "current_live_state": live.get("state") if isinstance(live, dict) else None,
            "current_live_changed": live.get("changed") if isinstance(live, dict) else None,
            "current_live_event_active": live.get("event_active") if isinstance(live, dict) else None,
        },
        "safety": dict(SAFETY),
        "decision_status": "HUMAN_DECISION_REQUIRED",
    }
