"""ANVIQO Intelligence Orchestrator.

A thin, tenant-safe composition layer over existing ANVIQO intelligence.
It does not create a replacement reasoning engine, does not mutate V5/PCI,
and never performs PLC/SCADA writes. It turns the existing evidence into one
consistent investigation contract: intent -> evidence -> context -> risk ->
next human decision.
"""
from __future__ import annotations

import re
from typing import Any, Callable

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "human_decision_required": True,
    "v5_intelligence_modified": False,
}

INTENTS = {
    "plant_brief": ("how is my plant", "plant health", "overall plant", "plant status", "plant condition"),
    "what_changed": ("what changed", "change", "changed", "since last", "recent change"),
    "root_cause": ("why", "root cause", "cause", "reason", "because"),
    "history": ("before", "previous", "previously", "has this happened", "history", "last time"),
    "maintenance": ("maintenance", "repair", "service", "calibration", "work order"),
    "spares": ("spare", "spares", "stock", "inventory", "critical spare"),
    "prediction": ("predict", "prediction", "early warning", "risk", "failure", "failing"),
    "events": ("event", "events", "alarm", "alarms", "timeline"),
    "shift": ("shift", "shift report", "handover", "handover report"),
    "management": ("hod", "management", "executive", "daily brief", "management brief"),
    "energy": ("energy", "power", "kwh", "consumption"),
    "production": ("production", "throughput", "output", "downtime", "loss"),
    "safety": ("safety", "permit", "trip", "interlock", "hazard"),
    "instrument": ("instrument", "instruments", "pressure", "temperature", "flow", "level", "transmitter"),
    "equipment": ("equipment", "machine", "asset", "motor", "fan", "pump", "mill"),
    "plc_io": ("plc", "i/o", " io ", "input", "output", "panel", "tb", "jb", "address"),
    "evidence": ("evidence", "source", "document", "drawing", "prove", "show me"),
    "memory": ("memory", "learned", "worked before", "what worked"),
}


def classify(question: str) -> list[str]:
    low = " " + re.sub(r"[^a-z0-9/ -]+", " ", str(question or "").lower()) + " "
    hits = []
    for intent, phrases in INTENTS.items():
        if any(p in low for p in phrases):
            hits.append(intent)
    return hits or ["knowledge"]


def _safe_call(fn: Callable[..., Any] | None, *args, **kwargs):
    if not callable(fn):
        return None
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _tenant_only(value: Any, plant_id: str):
    """Accept optional legacy evidence only when it explicitly belongs to plant."""
    if value is None:
        return None
    if isinstance(value, dict):
        tagged = value.get("plant_id")
        if tagged and str(tagged) != str(plant_id):
            return None
        return value
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict) and item.get("plant_id") and str(item.get("plant_id")) != str(plant_id):
                continue
            out.append(item)
        return out
    return value


def _module_evidence(plant_id: str, tag: str | None = None) -> dict[str, Any]:
    """Reuse existing engines opportunistically; never trust unscoped evidence."""
    out: dict[str, Any] = {}
    if not tag:
        return out
    loaders = {
        "equipment": ("equipment_database", "get_equipment"),
        "health": ("equipment_health", "get_health_history"),
        "prediction": ("predictive_history", "get_predictions"),
        "events": ("event_timeline", "get_events"),
        "memory": ("learning_bridge", "get_learning_evidence"),
        "patterns": ("pattern_context", "get_equipment_patterns"),
        "maintenance": ("maintenance_actions", "get_maintenance_actions"),
    }
    for key, (module_name, fn_name) in loaders.items():
        try:
            module = __import__(module_name)
            fn = getattr(module, fn_name, None)
            value = _safe_call(fn, tag)
            value = _tenant_only(value, plant_id)
            if value not in (None, [], {}):
                out[key] = value
        except Exception:
            continue
    return out


def _extract_tag(question: str) -> str | None:
    for token in re.findall(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b", str(question or "")):
        n = re.sub(r"[^A-Za-z0-9]", "", token).upper()
        if re.match(r"^[A-Z]{1,12}\d{1,6}$", n):
            return n
    return None


def build_brief(plant_id: str, plant_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [r for r in rows if isinstance(r, dict)]
    areas = sorted({str(r.get("area")) for r in rows if r.get("area")})
    sources = sorted({str(r.get("source")) for r in rows if r.get("source")})
    tags = sorted({str(r.get("tag") or r.get("external_id")) for r in rows if r.get("tag") or r.get("external_id")})
    types: dict[str, int] = {}
    for r in rows:
        key = str(r.get("record_type") or "knowledge")
        types[key] = types.get(key, 0) + 1
    evidence = "HIGH" if rows and sources else ("MEDIUM" if rows else "LOW")
    return {
        "status": "EVIDENCE_AVAILABLE" if rows else "INSUFFICIENT_EVIDENCE",
        "plant_id": plant_id,
        "plant_name": plant_name,
        "summary": f"{plant_name}: {len(rows)} onboarded knowledge record(s), {len(tags)} indexed tag(s), {len(areas)} area(s), {len(sources)} source document(s).",
        "evidence_confidence": evidence,
        "coverage": {"records": len(rows), "tags": len(tags), "areas": len(areas), "sources": len(sources)},
        "record_types": types,
        "areas": areas[:100],
        "sources": sources[:50],
        "next_questions": [
            "What changed?",
            "Why is it important?",
            "Has this happened before?",
            "Show me the evidence.",
        ],
        **SAFETY,
    }


def investigate(question: str, plant_id: str, plant_name: str, answer_fn: Callable[[str], Any], rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return a single product-level investigation envelope around existing ANVI answers."""
    intents = classify(question)
    answer = _safe_call(answer_fn, question)
    if not isinstance(answer, dict):
        answer = {"answer": str(answer or "")}
    tag = _extract_tag(question)
    legacy = _module_evidence(plant_id, tag)
    evidence = answer.get("evidence") if isinstance(answer.get("evidence"), list) else []
    if rows:
        evidence = evidence or rows[:8]
    status = answer.get("evidence_status") or ("EVIDENCE_AVAILABLE" if evidence else "INSUFFICIENT_EVIDENCE")
    brief = {
        "intent": intents,
        "primary_intent": intents[0],
        "answer": answer.get("answer", ""),
        "evidence_status": status,
        "evidence_count": len(evidence),
        "evidence": evidence[:8],
        "context": {"plant_id": plant_id, "plant_name": plant_name, "tag": tag},
        "existing_intelligence": legacy,
        "why_this_matters": "ANVI separates evidence from interpretation; an available signal is not treated as proof of causation.",
        "recommended_human_step": "Review the cited evidence and make the operational decision through the existing approved plant procedure.",
        "decision": {"required": True, "automatic_action": False},
        **SAFETY,
    }
    return brief


__all__ = ["SAFETY", "INTENTS", "classify", "build_brief", "investigate"]
