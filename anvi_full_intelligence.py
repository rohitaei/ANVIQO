"""ANVIQO Full Intelligence Orchestrator.

One deterministic orchestration layer for the existing V5/V2 intelligence
engines. It does not replace frozen engines and never performs PLC/SCADA writes.
The module collects only selected-plant evidence and exposes a compact context
packet for conversational ANVI.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def _ctx():
    try:
        from flask import session
        return (
            str(session.get("plant_id") or "").strip(),
            str(session.get("organization_id") or "").strip(),
            str(session.get("plant_name") or "").strip(),
        )
    except Exception:
        return "", "", ""


def _tag(q: str) -> str:
    m = re.search(r"\b[A-Za-z]{1,12}[-_ ]?\d{1,6}\b", str(q or ""))
    return m.group(0).upper() if m else ""


def _norm(v: Any) -> str:
    return re.sub(r"[-_ ]", "", str(v or "")).lower()


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def build_context(question: str) -> Dict[str, Any]:
    """Build a selected-plant evidence packet from existing intelligence."""
    pid, oid, plant_name = _ctx()
    out: Dict[str, Any] = {
        "plant": {
            "plant_id": pid,
            "organization_id": oid,
            "plant_name": plant_name or "selected plant",
            "scope": "SELECTED_PLANT_ONLY",
        } if pid else "MISSING",
        "safety": dict(SAFETY),
        "question": str(question or ""),
        "tag": _tag(question),
        "sources": [],
    }

    if not pid:
        return out

    tag = out["tag"]

    # Master intelligence fabric: reuse the already-built V5/V2 engines as one
    # evidence packet. This is deliberately additive; no frozen engine is replaced.
    try:
        from anviqo_intelligence_fabric import build_realtime_evidence_state
        fabric = build_realtime_evidence_state(question, tag or None)
        if isinstance(fabric, dict):
            out["intelligence_fabric"] = fabric
            out["sources"].append("INTELLIGENCE_FABRIC")
    except Exception:
        out["intelligence_fabric"] = None

    # Universal capability engine: exactly 5,000 addressable contracts,
    # with runtime coverage derived from real backing modules.
    try:
        from anvi_capability_engine import manifest as capability_manifest
        out["capability_engine"] = capability_manifest()
        out["sources"].append("UNIVERSAL_CAPABILITY_ENGINE")
    except Exception:
        out["capability_engine"] = None

    # Product capability map: the roadmap capabilities already implemented in
    # the repository are exposed through one stable contract for ANVI. This is
    # metadata only; evidence still has to come from the selected plant.
    out["capabilities"] = {
        "digital_plant": True,
        "digital_equipment_identity": True,
        "equipment_twin": True,
        "evidence_graph": True,
        "digital_thread": True,
        "real_time_observation": True,
        "plant_state": True,
        "operating_envelope": True,
        "event_correlation": True,
        "what_changed": True,
        "attention_intelligence": True,
        "plant_health": True,
        "predictive_intelligence": True,
        "diagnosis": True,
        "maintenance_intelligence": True,
        "critical_spares": True,
        "plant_memory": True,
        "shift_intelligence": True,
        "management_hod_intelligence": True,
        "risk_consequence": True,
        "decision_simulation": True,
        "plant_replay": True,
        "outcome_learning": True,
        "universal_onboarding": True,
        "conversational_anvi": True,
        "voice_anvi": True,
        "tenant_isolation": True,
        "human_governance": True,
    }

    # Live observation / operating state.
    try:
        from pci_live_simulator import get_live_pci_snapshot
        snap = get_live_pci_snapshot() or {}
        if str(snap.get("mode") or "").upper() == "SIMULATION":
            out["live_observation"] = {
                k: snap.get(k)
                for k in (
                    "mode", "source", "total_io", "healthy", "warning",
                    "critical", "changed", "active_events", "plant_health_score",
                    "areas",
                )
            }
            points = snap.get("points") or []
            if tag:
                wanted = _norm(tag)
                p = next(
                    (x for x in points if isinstance(x, dict) and _norm(x.get("tag")) == wanted),
                    None,
                )
                if p:
                    out["requested_point"] = {
                        k: p.get(k) for k in (
                            "tag", "description", "area", "service", "value",
                            "state", "changed", "event_active", "io_type",
                            "plc_address", "source",
                        )
                    }
            out["attention_points"] = [
                {
                    k: p.get(k) for k in (
                        "tag", "description", "area", "value", "state",
                        "changed", "event_active", "io_type", "plc_address",
                    )
                }
                for p in points
                if isinstance(p, dict) and (
                    p.get("changed") or p.get("event_active") or
                    str(p.get("state") or "").upper() in ("WARNING", "CRITICAL")
                )
            ][:50]
            out["sources"].append("PCI_LIVE_SIMULATOR")
    except Exception:
        pass

    # Persistent selected-plant knowledge.
    try:
        from anvi_chat_stability_v2 import _query_rows, _terms
        rows = (
            _query_rows(pid, oid, identifier=tag, limit=25)
            if tag else _query_rows(pid, oid, terms=_terms(question), limit=30)
        )
        out["knowledge"] = [r for r in (rows or []) if isinstance(r, dict)]
        if out["knowledge"]:
            out["sources"].append("SELECTED_PLANT_KNOWLEDGE")
    except Exception:
        out["knowledge"] = []

    # Simulation event stream.
    try:
        from v2_simulation_state import get as get_sim
        out["events"] = get_sim(pid, tag=tag or None)[-50:]
        if out["events"]:
            out["sources"].append("V2_SIMULATION_EVENTS")
    except Exception:
        out["events"] = []

    # Existing equipment identity / relationships.
    if tag:
        try:
            from equipment_database import get_equipment
            identity = get_equipment(tag)
            if identity:
                out["equipment_identity"] = identity
                out["sources"].append("EQUIPMENT_IDENTITY")
        except Exception:
            pass
        try:
            from equipment_relationships import build_equipment_relationships
            rel = build_equipment_relationships(tag)
            if rel:
                out["relationships"] = rel
                out["sources"].append("EQUIPMENT_RELATIONSHIPS")
        except Exception:
            pass

    # Existing root-cause intelligence is included as evidence, not blindly
    # converted into a confirmed cause.
    if tag and any(x in str(question).lower() for x in (
        "why", "root cause", "cause", "fault", "failure", "problem", "issue"
    )):
        try:
            from root_cause_intelligence import build_root_cause_intelligence
            rci = build_root_cause_intelligence(question, tag)
            if isinstance(rci, dict):
                out["diagnosis"] = {
                    "status": rci.get("status"),
                    "conclusion": rci.get("conclusion"),
                    "observed_condition": rci.get("observed_condition"),
                    "evidence_summary": rci.get("evidence_summary"),
                    "hypotheses": rci.get("hypotheses"),
                }
                out["sources"].append("ROOT_CAUSE_INTELLIGENCE")
        except Exception:
            pass

    # Maintenance/spare context is read-only here; mutation remains in the
    # existing authorized inventory routes.
    if tag:
        try:
            from maintenance_experience_matching import find_matching_experience
            matches = find_matching_experience({"equipment": tag, "tag": tag, "query": question})
            if isinstance(matches, list):
                out["maintenance_matches"] = matches[:20]
                if matches:
                    out["sources"].append("MAINTENANCE_EXPERIENCE")
        except Exception:
            out["maintenance_matches"] = []

        try:
            from pci_spares import _v18_bf2_exact
            rows = _v18_bf2_exact(tag, pid)
            if rows:
                r = rows[0]
                out["spare"] = {
                    "tag": tag,
                    "available": int(r.get("qty_available") or 0),
                    "instrument": r.get("instrument"),
                    "area": r.get("area"),
                    "source": r.get("source"),
                }
                out["sources"].append("SPARE_REGISTRY")
        except Exception:
            pass

    # Compact, deterministic state summary for downstream reasoning.
    point = out.get("requested_point") or {}
    live = out.get("live_observation") or {}
    out["state_summary"] = {
        "current_state": point.get("state"),
        "current_value": point.get("value"),
        "changed": point.get("changed"),
        "event_active": point.get("event_active"),
        "plant_health_score": live.get("plant_health_score"),
        "attention_count": len(out.get("attention_points") or []),
        "event_count": len(out.get("events") or []),
        "knowledge_count": len(out.get("knowledge") or []),
        "evidence_available": bool(out.get("sources")),
    }
    return out
