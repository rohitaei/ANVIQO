"""
ANVIQO KNOWLEDGE LAYER
Conversational front door to the existing V5 intelligence stack.

Rules:
- Reuses existing intelligence.
- No duplicate reasoning engines.
- Read-only.
- No PLC/SCADA control.
- Human decision required.
"""

import json
import os
import re
from collections import Counter


PCI_PATH = os.path.join(
    "database", "pci", "pci_instrument_database.json"
)


def _pci():
    with open(PCI_PATH, encoding="utf-8") as f:
        return json.load(f)


def _records():
    return _pci().get("records", [])


def _tag_from_question(q):
    tags = re.findall(r"\b[A-Za-z]{1,8}[-_][A-Za-z0-9_]+\b", q.upper())
    records = _records()
    known = {str(x.get("tag", "")).upper(): x for x in records}

    for tag in tags:
        if tag in known:
            return tag, known[tag]

    for x in records:
        tag = str(x.get("tag", "")).strip()
        if tag and tag.lower() in q.lower():
            return tag, x

    return None, None


def _pci_answer(q):
    ql = q.lower()
    records = _records()

    tag, item = _tag_from_question(q)

    if tag and item:
        return (
            f"ANVI found verified PCI evidence for {tag}. "
            f"{item.get('description','No description available')}. "
            f"Area: {item.get('area','UNKNOWN')}. "
            f"I/O type: {item.get('io_type','UNKNOWN')}. "
            f"PLC address: {item.get('plc_address','UNKNOWN')}. "
            f"Panel: {item.get('panel','UNKNOWN')}. "
            f"TB: {item.get('tb_name','UNKNOWN')} "
            f"{item.get('tb_no','')}. "
            f"Source: {item.get('source_sheet','UNKNOWN')}. "
            f"Criticality: {item.get('criticality','NOT CLASSIFIED')}."
        )

    if any(x in ql for x in ["how many", "count", "total", "number"]):
        if "di" in ql:
            n = sum(x.get("io_type") == "DI" for x in records)
            return f"ANVI found {n} DI records in the verified PCI database."

        if "do" in ql:
            n = sum(x.get("io_type") == "DO" for x in records)
            return f"ANVI found {n} DO records in the verified PCI database."

        if "ai" in ql:
            n = sum(str(x.get("io_type","")).startswith("AI") for x in records)
            return f"ANVI found {n} AI records in the verified PCI database."

        if "ao" in ql:
            n = sum(str(x.get("io_type","")).startswith("AO") for x in records)
            return f"ANVI found {n} AO records in the verified PCI database."

        return (
            f"ANVI found {len(records)} verified instrumentation I/O "
            f"records in the PCI database."
        )

    if "critical" in ql:
        critical = [
            x for x in records
            if str(x.get("criticality","")).upper() == "HIGH"
        ]

        if not critical:
            return "ANVI found no instruments currently classified HIGH criticality."

        return (
            f"ANVI found {len(critical)} HIGH-criticality instruments: "
            + "; ".join(
                f"{x.get('tag')} — {x.get('description','')} "
                f"({x.get('area','UNKNOWN')})"
                for x in critical
            ) + "."
        )

    areas = Counter(x.get("area","UNKNOWN") for x in records)
    ios = Counter(x.get("io_type","UNKNOWN") for x in records)

    if "area" in ql:
        return (
            f"ANVI has verified PCI coverage across {len(areas)} areas. "
            + ", ".join(f"{k}: {v}" for k,v in areas.most_common())
            + "."
        )

    return (
        f"ANVI has access to the verified PCI evidence layer: "
        f"{len(records)} I/O records across {len(areas)} areas. "
        f"I/O distribution: "
        + ", ".join(f"{k}: {v}" for k,v in ios.items())
        + ". The database is read-only."
    )


def _call(fn, *args):
    try:
        result = fn(*args)
        if isinstance(result, dict):
            return result
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


def _equipment(q):
    from anviqo_product import AnviqoProduct

    tag, item = _tag_from_question(q)

    if not tag:
        m = re.search(
            r"\b(CV|PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|P|FV|XV)[-_]?\d+\b",
            q.upper()
        )
        if m:
            tag = m.group(0).replace("_", "-")

    if not tag:
        return None

    p = AnviqoProduct()
    result = p.equipment_view(tag)

    if result.get("status") == "NO DATA" and item:
        return _pci_answer(q)

    return (
        f"ANVI equipment intelligence for {tag}: "
        + json.dumps(result, ensure_ascii=False)
    )


def _build_area_results():
    """
    Build area-health evidence using the existing V5 area-health engine.
    No new health/reasoning logic is created here.
    """
    from equipment_database import get_equipment
    from area_health import build_area_health

    equipment = get_equipment() or []

    areas = []
    seen = set()

    for item in equipment:
        area = str(item.get("area", "")).strip()
        if not area:
            continue

        key = area.upper()
        if key in seen:
            continue

        seen.add(key)
        areas.append(area)

    return [
        build_area_health(area)
        for area in areas
    ]


def _plant(q):
    from anviqo_product import AnviqoProduct

    p = AnviqoProduct()
    ql = q.lower()

    area_results = _build_area_results()

    if "what changed" in ql or "changed" in ql:
        from plant_what_changed import build_plant_what_changed

        result = build_plant_what_changed(
            "PLANT",
            area_results,
            equipment_events=[]
        )

        return "ANVI — What Changed:\n" + json.dumps(
            result, ensure_ascii=False
        )

    if "health" in ql:
        from plant_health_intelligence import build_plant_health_intelligence

        result = build_plant_health_intelligence(
            "PLANT",
            area_results
        )

        return "ANVI — Plant Health:\n" + json.dumps(
            result, ensure_ascii=False
        )

    if "event" in ql or "chain" in ql:
        result = p.event_timeline("CV-101")
        return "ANVI — Event Intelligence:\n" + json.dumps(
            result, ensure_ascii=False
        )

    result = p.plant_brain("PLANT")
    return "ANVI — Plant Brain:\n" + json.dumps(
        result, ensure_ascii=False
    )


def _maintenance(q):
    ql = q.lower()

    from maintenance_recommendations import (
        build_maintenance_recommendation
    )
    from maintenance_patterns import normalize_pattern

    tag, item = _tag_from_question(q)

    if tag:
        pattern_source = " ".join([
            str(item.get("description", "")) if item else "",
            q
        ])
    else:
        pattern_source = q

    pattern = normalize_pattern(pattern_source)

    recommendation = build_maintenance_recommendation(
        pattern
    )

    if (
        "recommend" in ql
        or "action" in ql
        or "what should" in ql
        or "maintenance" in ql
        or "repair" in ql
        or "inspection" in ql
        or "fix" in ql
    ):
        return "ANVI — Maintenance Intelligence:\n" + json.dumps(
            {
                "equipment": tag or "NOT IDENTIFIED",
                "pattern": pattern,
                "recommendation": recommendation,
                "read_only": True,
                "human_decision_required": True
            },
            ensure_ascii=False
        )

    from maintenance_management_report import build_management_report

    equipment_name = tag or "PLANT"
    area = (
        item.get("area", "UNKNOWN")
        if item
        else "UNKNOWN"
    )

    current_condition = {
        "equipment": equipment_name,
        "area": area,
        "reason": (
            f"ANVI evaluated the existing maintenance evidence "
            f"for pattern {pattern}."
        )
    }

    base_recommendation = {
        "priority": 0,
        "recommendation": recommendation.get(
            "message",
            "No verified maintenance recommendation available."
        )
    }

    result = build_management_report(
        current_condition,
        base_recommendation
    )

    return "ANVI — Maintenance / Management Intelligence:\n" + json.dumps(
        result, ensure_ascii=False
    )


def _executive(q):
    from v57_executive_intelligence import build_executive_intelligence

    result = build_executive_intelligence()
    return "ANVI — Executive Intelligence:\n" + json.dumps(
        result, ensure_ascii=False
    )


def ask_anvi(question):
    q = (question or "").strip()

    if not q:
        return {
            "answer": "Please ask ANVI a question.",
            "domain": "general"
        }

    ql = q.lower()

    try:
        # PCI / instrumentation evidence
        if any(x in ql for x in [
            "pci", "instrument", "i/o", " io ",
            "critical instrument", "plc tag",
            "instrument tag", "transmitter", "control valve",
            "flow meter", "pressure transmitter",
            "temperature transmitter", "level transmitter"
        ]):
            return __import__("pci_conversation").answer(q)

        # Equipment
        if re.search(
            r"\b(CV|PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|P|FV|XV)[-_]?\d+\b",
            q.upper()
        ):
            return {
                "answer": _equipment(q),
                "domain": "equipment",
                "read_only": True
            }

        # Maintenance
        if any(x in ql for x in [
            "maintenance", "repair", "recommendation",
            "recommended action", "what should i check",
            "what should we check", "fix", "inspection"
        ]):
            return {
                "answer": _maintenance(q),
                "domain": "maintenance",
                "read_only": True,
                "human_decision_required": True
            }

        # Management / HOD
        if any(x in ql for x in [
            "management", "hod", "executive",
            "decision", "priority", "management report"
        ]):
            return {
                "answer": _executive(q),
                "domain": "executive",
                "read_only": True,
                "human_decision_required": True
            }

        # Plant / event / health / situation
        if any(x in ql for x in [
            "plant", "health", "changed", "event",
            "events", "event chain", "situation",
            "condition", "status", "risk"
        ]):
            return {
                "answer": _plant(q),
                "domain": "plant",
                "read_only": True,
                "human_decision_required": True
            }

        return {
            "answer": (
                "ANVI is connected to the ANVIQO intelligence core. "
                "Ask me naturally about instruments, equipment, plant "
                "condition, risks, events, maintenance, recommendations, "
                "management decisions or verified evidence."
            ),
            "domain": "general",
            "capabilities": [
                "Instrumentation / PCI",
                "Equipment Intelligence",
                "Plant Health",
                "What Changed",
                "Event Intelligence",
                "Maintenance Intelligence",
                "Management Intelligence",
                "Executive Intelligence",
                "Plant Brain"
            ],
            "read_only": True
        }

    except Exception as e:
        return {
            "answer": (
                "ANVI could not complete that intelligence request. "
                f"Evidence-layer error: {e}"
            ),
            "domain": "error",
            "read_only": True
        }
