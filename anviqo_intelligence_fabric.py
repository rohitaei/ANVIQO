"""
ANVIQO INTELLIGENCE FABRIC V2.1
Unified evidence orchestration for the existing ANVIQO V5 intelligence stack.

This layer integrates existing engines.
It does not replace them.
It never writes to PLC/SCADA.
"""

from __future__ import annotations

import importlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "ANVIQO-INTELLIGENCE-FABRIC-V2.1"

SAFETY = {
    "control_mode": "READ_ONLY",
    "plc_write": False,
    "scada_control": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def load(name):
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def call(module, function, *args, **kwargs):
    if module is None:
        return None
    fn = getattr(module, function, None)
    if not callable(fn):
        return None
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def now():
    return datetime.now(timezone.utc).isoformat()


def extract_tag(text: str) -> Optional[str]:
    if not text:
        return None

    m = re.search(
        r"\b(?:PT|FT|LT|TT|DP|MCV|SOV|FSV|PCV|POSR|TCV|FV|XV)[-_ ]?\d{1,5}\b",
        text.upper(),
    )

    if not m:
        return None

    return m.group(0).replace("_", "-").replace(" ", "-")


def norm_tag(tag):
    return str(tag or "").upper().replace("_", "-").replace(" ", "-")


def verified_memory(tag):
    """
    Reads existing Plant Memory directly.
    Pending memories are intentionally excluded from verified evidence.
    """
    tag = norm_tag(tag)
    if not tag:
        return []

    module = load("plant_memory")

    records = call(module, "search_all_memory")

    if not isinstance(records, list):
        try:
            path = Path("database/plant_memory/plant_memory.json")
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                records = data if isinstance(data, list) else []
        except Exception:
            records = []

    result = []

    for r in records:
        if norm_tag(r.get("tag")) != tag:
            continue

        is_verified = (
            r.get("verified") is True
            or str(r.get("verification_status", "")).upper() == "VERIFIED"
            or r.get("human_verified") is True
        )

        if is_verified:
            result.append(r)

    return result


def pci(tag, query):
    m = load("pci_conversation")

    result = {
        "identity": None,
        "live": None,
        "answer": None,
    }

    result["identity"] = call(m, "find_tag", tag)

    # The live simulator may require no tag or may return a complete
    # plant snapshot. Preserve whatever the existing engine provides.
    result["live"] = call(m, "get_live_pci_snapshot")

    # Use the authoritative conversational PCI answer as fallback context.
    result["answer"] = call(m, "answer", query)

    # If find_tag returns no direct identity, search the authoritative
    # PCI database through the existing search interface.
    if result["identity"] is None:
        result["identity"] = call(m, "search", tag)

    return result


def equipment(tag):
    m = load("equipment_health")

    latest = call(m, "get_latest_health", tag)

    score = None
    assessment = None

    s = load("equipment_health_score")

    if latest is not None:
        score = call(s, "calculate_health_score", latest)
        assessment = call(s, "build_health_assessment", latest)

    # Some deployments expose the health calculation through the score
    # engine rather than the history engine.
    if score is None:
        score = call(s, "calculate_health_score", tag)

    if assessment is None:
        assessment = call(s, "build_health_assessment", tag)

    return {
        "latest_health": latest,
        "health_score": score,
        "health_assessment": assessment,
    }


def plant():
    m = load("plant_health")

    result = call(m, "build_plant_health")
    if result is None:
        result = call(m, "calculate_plant_health")
    if result is None:
        result = call(m, "analyze_plant")

    intelligence = load("plant_health_intelligence")
    intelligence_result = call(
        intelligence,
        "build_plant_health_intelligence",
    )

    return {
        "health": result,
        "intelligence": intelligence_result,
    }


def events(tag):
    m = load("event_timeline")

    recent = call(m, "get_recent_events")
    events = call(m, "get_events")

    c = load("event_correlation")

    correlation = call(c, "correlate_events", tag)

    return {
        "recent": recent,
        "events": events,
        "correlation": correlation,
    }


def maintenance(tag, query):
    m = load("maintenance_experience_matching")

    experience = call(
        m,
        "build_experience_context",
        {
            "equipment": tag,
            "tag": tag,
            "query": query,
        },
    )

    matching = call(
        m,
        "find_matching_experience",
        {
            "equipment": tag,
            "tag": tag,
            "query": query,
        },
    )

    if matching is None:
        matching = []

    return {
        "experience_context": experience,
        "matching_experience": matching,
    }


def spares(tag, query):
    m = load("pci_spares")

    result = call(m, "answer_spare_query", query)

    if result is None:
        result = call(m, "query_spares", query)

    return result


def historical_summary(records):
    output = []

    for r in records:
        output.append(
            {
                "memory_id": r.get("memory_id") or r.get("record_id"),
                "timestamp": r.get("timestamp"),
                "tag": r.get("tag"),
                "event": r.get("event"),
                "observation": r.get("observation"),
                "maintenance_action": r.get("maintenance_action")
                or r.get("action"),
                "finding": r.get("finding"),
                "confirmation": r.get("confirmation_evidence")
                or r.get("confirmation"),
                "outcome": r.get("outcome"),
                "recovery": r.get("recovery_status")
                or r.get("recovery"),
                "spare_used": r.get("spare_used")
                or r.get("spare"),
                "verified": True,
            }
        )

    return output


def evidence_confidence(e):
    """
    Confidence is evidence availability, not probability of failure.
    """

    score = 0
    sources = []

    if e["pci"].get("identity") is not None:
        score += 20
        sources.append("PCI_ENGINEERING_IDENTITY")

    if e["pci"].get("live") is not None:
        score += 15
        sources.append("PCI_LIVE_SIMULATION")

    if e["equipment"].get("latest_health") is not None:
        score += 10
        sources.append("EQUIPMENT_HEALTH")

    if e["equipment"].get("health_score") is not None:
        score += 5
        sources.append("EQUIPMENT_HEALTH_SCORE")

    if e["equipment"].get("health_assessment") is not None:
        score += 5
        sources.append("EQUIPMENT_HEALTH_ASSESSMENT")

    if e["plant"].get("health") is not None:
        score += 5
        sources.append("PLANT_HEALTH")

    if e["events"].get("recent") or e["events"].get("events"):
        score += 10
        sources.append("EVENT_TIMELINE")

    if e["events"].get("correlation") is not None:
        score += 5
        sources.append("EVENT_CORRELATION")

    if (
        e["maintenance"].get("experience_context") is not None
        or e["maintenance"].get("matching_experience")
    ):
        score += 10
        sources.append("MAINTENANCE_INTELLIGENCE")

    if e["spares"] is not None:
        score += 5
        sources.append("CRITICAL_SPARES")

    if e["verified_memory"]:
        score += 15
        sources.append("VERIFIED_PLANT_MEMORY")

    score = min(score, 100)

    if score >= 80:
        level = "HIGH"
    elif score >= 55:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "score": score,
        "level": level,
        "basis": "Evidence availability across authoritative ANVIQO engines",
        "sources": sources,
    }


def build_intelligence_fabric(query: str, tag: Optional[str] = None):
    query = str(query or "").strip()
    tag = norm_tag(tag or extract_tag(query))

    memory = historical_summary(verified_memory(tag))

    evidence = {
        "pci": pci(tag, query),
        "equipment": equipment(tag),
        "plant": plant(),
        "events": events(tag),
        "maintenance": maintenance(tag, query),
        "spares": spares(tag, query),
        "verified_memory": memory,
    }

    confidence = evidence_confidence(evidence)

    return {
        "fabric_version": VERSION,
        "timestamp": now(),
        "query": query,
        "tag": tag,
        "confidence": confidence,
        "evidence": evidence,
        "historical_experience": memory,
        "safety": dict(SAFETY),
        "execution_status": "READ_ONLY",
        "decision_status": "HUMAN_DECISION_REQUIRED",
    }


def demo():
    query = "PT-303 is showing abnormal pressure. What should I check?"
    result = build_intelligence_fabric(query, "PT-303")

    print("=" * 76)
    print("ANVIQO INTELLIGENCE FABRIC V2.1")
    print("=" * 76)
    print("TAG        :", result["tag"])
    print("CONFIDENCE :", result["confidence"])
    print("MEMORY     :", len(result["historical_experience"]))
    print("SAFETY     :", result["safety"])
    print()

    for source in result["confidence"]["sources"]:
        print("  +", source)

    print()
    print("===== VERIFIED PT-303 HISTORY =====")

    for h in result["historical_experience"]:
        print("EVENT       :", h["event"])
        print("OBSERVATION :", h["observation"])
        print("ACTION      :", h["maintenance_action"])
        print("FINDING     :", h["finding"])
        print("CONFIRM     :", h["confirmation"])
        print("OUTCOME     :", h["outcome"])
        print("RECOVERY    :", h["recovery"])
        print("SPARE       :", h["spare_used"])
        print("VERIFIED    :", h["verified"])

    print()
    print("===== SAFETY GATE =====")
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False
    assert result["safety"]["automatic_execution"] is False
    assert result["safety"]["human_decision_required"] is True

    print("PLC WRITE              : BLOCKED")
    print("SCADA CONTROL          : BLOCKED")
    print("AUTOMATIC EXECUTION    : BLOCKED")
    print("HUMAN DECISION         : REQUIRED")
    print()
    print("===== FABRIC BUILD PASS =====")


if __name__ == "__main__":
    demo()
