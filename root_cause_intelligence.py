"""
ANVIQO Root Cause Intelligence V1

Evidence-backed diagnostic hypothesis generation over existing ANVIQO engines.
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


VERSION = "ANVIQO-RCI-V1.0"
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
    if not q:
        return False

    equipment = bool(_EQUIPMENT_RE.search(q))
    if not equipment:
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

    # A direct "why is/was/did/has..." equipment question is itself an
    # investigation request even when the symptom word is omitted.
    direct_why = any(term in q for term in ("why is", "why was", "why did", "why has", "why does", "why are", "why were"))
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
    return str(tag or "").upper().replace("_", "-").replace(" ", "-")


def extract_tag(text: str) -> Optional[str]:
    m = _EQUIPMENT_RE.search(str(text or ""))
    return _norm_tag(m.group(0)) if m else None


def _verified_memory(tag: str) -> List[Dict[str, Any]]:
    module = _load("plant_memory")
    records = _call(module, "search_all_memory", query="", tag=tag, limit=50)
    if not isinstance(records, list):
        return []
    result = []
    for record in records:
        if not isinstance(record, dict):
            continue
        if _norm_tag(record.get("tag")) != tag:
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
    events = _call(module, "get_events", tag)
    return events if isinstance(events, list) else []


def _health(tag: str):
    module = _load("equipment_health")
    return _call(module, "get_latest_health", tag)


def _maintenance(tag: str, query: str):
    module = _load("maintenance_experience_matching")
    context = {"equipment": tag, "tag": tag, "query": query}
    experience = _call(module, "build_experience_context", context)
    matching = _call(module, "find_matching_experience", context)
    return experience, matching if isinstance(matching, list) else []


def _text(records: List[Dict[str, Any]]) -> str:
    parts = []
    for record in records:
        for key in ("message", "event", "observation", "finding", "maintenance_action", "outcome"):
            value = record.get(key)
            if value:
                parts.append(str(value))
    return " ".join(parts).lower()


def _hypotheses(events: List[Dict[str, Any]], memory: List[Dict[str, Any]], health: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return ranked hypotheses only when explicit evidence supports them."""
    event_text = _text(events)
    memory_text = _text(memory)
    combined = f"{event_text} {memory_text}"
    candidates = []

    rules = [
        (
            "instrument-air / positioner issue",
            ("air pressure" in combined and ("valve position" in combined or "positioner" in combined)),
            "Explicit evidence links instrument-air/valve-position information in the available history.",
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

    for name, matched, rationale in rules:
        if not matched:
            continue
        evidence = []
        for source, records in (("EVENT_TIMELINE", events), ("VERIFIED_PLANT_MEMORY", memory)):
            for record in records:
                raw = " ".join(str(record.get(k) or "") for k in ("message", "event", "observation", "finding", "maintenance_action", "outcome"))
                if any(token in raw.lower() for token in name.split(" / ")) or name.startswith("process-condition"):
                    evidence.append({
                        "source": source,
                        "memory_id": record.get("memory_id"),
                        "timestamp": record.get("timestamp"),
                        "text": raw.strip(),
                    })
        candidates.append({
            "hypothesis": name,
            "status": "INVESTIGATE",
            "support": rationale,
            "evidence": evidence,
        })

    return candidates


def build_root_cause_intelligence(query: str, tag: Optional[str] = None) -> Dict[str, Any]:
    query = str(query or "").strip()
    tag = _norm_tag(tag or extract_tag(query))
    events = _events(tag) if tag else []
    memory = _verified_memory(tag) if tag else []
    health = _health(tag) if tag else None
    experience, matching = _maintenance(tag, query) if tag else (None, [])
    hypotheses = _hypotheses(events, memory, health if isinstance(health, dict) else {})

    if hypotheses:
        status = "HYPOTHESES_AVAILABLE"
        conclusion = "ANVIQO found evidence-supported hypotheses to investigate. These are not confirmed root causes."
    elif events or memory or health:
        status = "INSUFFICIENT_EVIDENCE"
        conclusion = "ANVIQO has relevant evidence but not enough explicit evidence to rank a root-cause hypothesis."
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
        "hypotheses": hypotheses,
        "evidence_summary": {
            "event_count": len(events),
            "verified_memory_count": len(memory),
            "health_available": health is not None,
            "maintenance_experience_available": experience is not None or bool(matching),
            "matching_experience_count": len(matching),
        },
        "safety": dict(SAFETY),
        "decision_status": "HUMAN_DECISION_REQUIRED",
    }
