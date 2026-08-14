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

    # --------------------------------------------------------
    # CONSOLIDATED CONVERSATIONAL ROUTING
    # Explicit current intent ALWAYS beats remembered context.
    # --------------------------------------------------------

    if _anvi_explicit_pci_question(q):
        return __import__("pci_conversation").answer(q)

    if _anvi_field_report_question(q):
        try:
            return __import__("pci_conversation").answer(q)
        except Exception:
            pass

    if _anvi_memory_question(q):
        try:
            return __import__("pci_plant_memory").search_reports(q)
        except Exception:
            try:
                return __import__("pci_plant_memory").similar_reports(q)
            except Exception:
                pass

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



def _pci_memory_route(question):
    """
    ANVIQO Plant Memory conversational router.

    This layer stores human field experience and retrieves
    previous experience. It does NOT create a new reasoning
    engine and does NOT claim automatic causation.
    """

    q = str(question or "").strip()
    ql = q.lower()

    memory_question = any(x in ql for x in [
        "have we seen this before",
        "seen this before",
        "previous experience",
        "previous report",
        "past experience",
        "past report",
        "similar problem",
        "similar issue",
        "similar failure",
        "history of this problem",
        "plant memory",
    ])

    field_report = any(x in ql for x in [
        "was not working",
        "wasn't working",
        "not working",
        "was faulty",
        "was failed",
        "checked and found",
        "found that",
        "found ",
        "inspection found",
        "during inspection",
        "technician checked",
        "operator checked",
        "air pressure was low",
        "pneumatic pressure was low",
        "pneumatic air pressure",
        "valve was jammed",
        "valve jammed",
        "controller was faulty",
        "controller fault",
        "replaced ",
        "repaired ",
        "restored ",
        "after repair",
        "after replacement",
        "issue resolved",
        "problem resolved",
        "failure occurred",
    ])

    if not memory_question and not field_report:
        return None

    from pci_plant_memory import (
        save_report,
        search_reports,
        similar_reports,
    )

    # --------------------------------------------------------
    # Find exact PCI tag from the 1064-record registry
    # --------------------------------------------------------

    tag = None

    try:
        from pci_registry import search

        registry = search(
            query=None,
            limit=1064
        )

        qu = q.upper()

        for item in registry:
            candidate = str(
                item.get("tag", "")
            ).strip()

            if candidate and candidate.upper() in qu:
                tag = candidate
                break

    except Exception:
        pass

    # --------------------------------------------------------
    # RETRIEVE PREVIOUS EXPERIENCE
    # --------------------------------------------------------

    if memory_question:

        results = similar_reports(
            q,
            tag=tag
        )

        if not results and tag:
            results = search_reports(
                tag=tag
            )

        if not results:
            return {
                "answer": (
                    "I could not find a previous human field report "
                    "matching this request. I will not invent plant "
                    "history."
                ),
                "domain": "pci_plant_memory",
                "evidence": "plant memory",
                "count": 0,
                "tag": tag,
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "human_verification_required": True,
            }

        return {
            "answer": (
                f"I found {len(results)} previous human field "
                "report(s)"
                + (f" associated with {tag}." if tag else ".")
                + " These are technician/operator experience "
                  "records. They are not automatically treated "
                  "as proven causation."
            ),
            "domain": "pci_plant_memory",
            "evidence": "plant memory",
            "count": len(results),
            "tag": tag,
            "reports": results,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_verification_required": True,
        }

    # --------------------------------------------------------
    # SAVE NEW HUMAN EXPERIENCE
    # --------------------------------------------------------

    entry = save_report(
        q,
        tag=tag,
        source="TECHNICIAN / OPERATOR REPORT"
    )

    previous = similar_reports(
        q,
        tag=tag
    )

    # Current report will normally appear in the similarity
    # results. Exclude its own memory_id when counting previous.
    previous = [
        x for x in previous
        if x.get("memory_id") != entry.get("memory_id")
    ]

    if previous:
        answer = (
            "I have saved this as a human field report."
            + (f" It is associated with {tag}." if tag else "")
            + f" I also found {len(previous)} previous related "
              "experience record(s). The reported cause remains "
              "unverified until a human confirms it."
        )
    else:
        answer = (
            "I have saved this as a human field report."
            + (f" It is associated with {tag}." if tag else "")
            + " The report is currently marked UNVERIFIED HUMAN "
              "REPORT. ANVI will not treat the reported cause as "
              "proven until a human verifies it."
        )

    return {
        "answer": answer,
        "domain": "pci_plant_memory",
        "evidence": "human field report",
        "memory_id": entry["memory_id"],
        "tag": tag,
        "previous_related_reports": len(previous),
        "verification_status": "UNVERIFIED HUMAN REPORT",
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "human_verification_required": True,
    }




# ============================================================
# ANVIQO CONVERSATIONAL CONTEXT ENGINE
# ============================================================

_ANVI_CONVERSATION_CONTEXT = {
    "last_pci_record": None,
    "last_pci_results": [],
    "last_equipment_tag": None,
    "last_domain": None,
}


def _pci_context_record(question):
    """
    Resolve PCI context in strict conversational order:

    1. Explicit instrument/tag in current question
    2. Existing conversational PCI record
    3. Verified PCI semantic lookup

    Never silently choose an unrelated instrument.
    """
    try:
        import pci_conversation as pc

        q = str(question or "").strip()

        # ----------------------------------------------------
        # 1. Explicit tag / exact PCI lookup
        # ----------------------------------------------------
        try:
            record = pc.find_tag(q)
            if record:
                return record
        except Exception:
            pass

        ids = re.findall(
            r"\\b[A-Za-z]{1,16}[-_][A-Za-z0-9_]+\\b",
            q.upper()
        )

        for ident in ids:
            try:
                record = pc.find_tag(ident)
                if record:
                    return record
            except Exception:
                pass

        # ----------------------------------------------------
        # 2. Conversational context
        # ----------------------------------------------------
        previous = _ANVI_CONVERSATION_CONTEXT.get("last_pci_record")

        if isinstance(previous, dict) and previous.get("tag"):
            return previous

        return None

    except Exception:
        return None


def _remember_pci_context(record=None, results=None):
    if isinstance(record, dict):
        _ANVI_CONVERSATION_CONTEXT["last_pci_record"] = record
        _ANVI_CONVERSATION_CONTEXT["last_equipment_tag"] = (
            record.get("tag")
        )
        _ANVI_CONVERSATION_CONTEXT["last_domain"] = "pci"

    if results is not None:
        _ANVI_CONVERSATION_CONTEXT["last_pci_results"] = list(results)


def _is_memory_question(q):
    ql = str(q or "").lower()

    return any(x in ql for x in [
        "have we seen this before",
        "seen this before",
        "seen this pattern before",
        "previous experience",
        "past experience",
        "previous report",
        "past report",
        "previous problem",
        "past problem",
        "last time",
        "earlier experience",
        "what happened before",
        "any previous",
    ])


def _is_pci_question(q):
    ql = str(q or "").lower()

    return any(x in ql for x in [
        "pci",
        "instrument",
        "i/o",
        " io ",
        "plc address",
        "plc tag",
        "instrument tag",
        "pressure transmitter",
        "pressure transmitters",
        "temperature transmitter",
        "level transmitter",
        "flow meter",
        "control valve",
        "terminal",
        "termination",
        "panel",
        "jb",
        "junction box",
        "tb",
        "valve",
        "transmitter",
    ])


def _pci_followup_question(q):
    """
    Questions that refer to the instrument currently being discussed.
    These may contain no instrument tag at all.
    """
    ql = str(q or "").lower()

    return any(x in ql for x in [
        "what is the plc address",
        "what's the plc address",
        "where is it",
        "which area is it",
        "what area is it",
        "which area",
        "what panel",
        "which panel",
        "what tb",
        "which tb",
        "which terminal",
        "terminal",
        "termination",
        "is it healthy",
        "is it working",
        "what is its status",
        "what is the status",
        "why is it critical",
        "why is it warning",
        "what changed",
        "what should i check",
        "what should we check",
        "what could be wrong",
        "what is wrong",
        "tell me more",
        "explain this instrument",
        "this transmitter",
        "this instrument",
    ])


def _remember_pci_context(record=None, results=None):
    if record:
        _ANVI_CONVERSATION_CONTEXT["last_pci_record"] = record

    if results is not None:
        _ANVI_CONVERSATION_CONTEXT["last_pci_results"] = list(results)


def _pci_context_answer(question, record):
    """
    Use the existing PCI conversation capability for the actual
    evidence response. This function only supplies conversational
    context; it does not duplicate PCI reasoning.
    """
    import pci_conversation as pc

    q = str(question or "").strip()

    # For a context-only follow-up, append the known tag so the
    # existing PCI evidence layer can answer against the correct record.
    tag = str(record.get("tag", "")).strip()

    if tag and not re.search(
        r"\b[A-Za-z]{1,16}[-_][A-Za-z0-9_]+\b",
        q
    ):
        q = f"{q} [{tag}]"

    result = pc.answer(q)

    _remember_pci_context(record=record)

    if isinstance(result, dict):
        result["context_tag"] = tag
        result["conversation_context"] = True

    return result



def _anvi_explicit_pci_question(question):
    ql=str(question or "").lower()

    phrases=[
        "pressure transmitter",
        "pressure transmitters",
        "temperature transmitter",
        "level transmitter",
        "flow meter",
        "flow meters",
        "control valve",
        "critical i/o",
        "critical io",
        "critical instruments",
        "which instruments",
        "which i/o",
        "which io",
        "show all",
        "list all",
        "vrm / mill",
        "vrm/mill",
        "vrm mill",
        "pci",
        "instrument tag",
        "plc tag",
    ]

    return any(x in ql for x in phrases)


def _anvi_field_report_question(question):
    ql=str(question or "").lower()

    markers=[
        "was not working",
        "not working",
        "was faulty",
        "checked",
        "found",
        "restored",
        "repaired",
        "replaced",
        "started working",
        "working again",
        "pneumatic air",
        "air pressure",
        "valve jam",
        "valve jammed",
        "controller fault",
        "controller was fault",
        "technician",
        "operator report",
        "field report",
    ]

    return any(x in ql for x in markers)


def _anvi_memory_question(question):
    ql=str(question or "").lower()

    markers=[
        "have we seen this before",
        "seen this before",
        "previous experience",
        "previous report",
        "past experience",
        "similar report",
        "similar reports",
        "last time",
        "previously",
        "earlier report",
        "plant memory",
    ]

    return any(x in ql for x in markers)




def _anvi_conversational_maintenance_answer(
    question,
    maintenance_result,
    pci_record=None,
):
    """
    Convert the existing V5 maintenance result into a technician-friendly
    conversational response.

    IMPORTANT:
    - Does not create new diagnostic reasoning.
    - Does not invent a failure cause.
    - Uses only information already returned by V5/PCI.
    """

    tag = ""
    description = ""
    area = ""
    plc_address = ""
    panel = ""
    tb = ""

    if isinstance(pci_record, dict):
        tag = str(pci_record.get("tag") or "").strip()
        description = str(
            pci_record.get("description") or ""
        ).strip()
        area = str(pci_record.get("area") or "").strip()
        plc_address = str(
            pci_record.get("plc_address") or ""
        ).strip()
        panel = str(pci_record.get("panel") or "").strip()
        tb = " ".join(
            str(x).strip()
            for x in [
                pci_record.get("tb_name") or "",
                pci_record.get("tb_no") or "",
            ]
            if str(x).strip()
        )

    if not isinstance(maintenance_result, dict):
        maintenance_result = {
            "raw_result": maintenance_result
        }

    # _maintenance() normally returns a JSON string prefixed by ANVI.
    raw = maintenance_result.get("raw_result")

    if raw is None:
        raw = maintenance_result.get("answer", "")

    import json

    data = None

    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, str):
        text = raw.strip()

        # Remove known ANVI prefix before parsing JSON.
        prefixes = [
            "ANVI — Maintenance Intelligence:",
            "ANVI — Maintenance / Management Intelligence:",
        ]

        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        try:
            data = json.loads(text)
        except Exception:
            data = None

    if not isinstance(data, dict):
        return {
            "answer": str(raw),
            "domain": "troubleshooting",
            "read_only": True,
            "human_decision_required": True,
        }

    recommendation = data.get("recommendation")

    if isinstance(recommendation, dict):
        recommendation_message = (
            recommendation.get("message")
            or recommendation.get("recommendation")
            or "No verified maintenance recommendation is available."
        )
        evidence_status = recommendation.get(
            "evidence_status",
            "UNKNOWN"
        )
    else:
        recommendation_message = (
            recommendation
            or "No verified maintenance recommendation is available."
        )
        evidence_status = data.get(
            "evidence_status",
            "UNKNOWN"
        )

    priority = data.get("priority")
    decision = data.get("decision")
    why = data.get("why") or []

    lines = []

    if tag:
        intro = f"{tag}"
        if description:
            intro += f" is {description}"
        if area:
            intro += f" in {area}"
        intro += "."

        lines.append(intro)

    if plc_address:
        lines.append(
            f"The verified PLC address is {plc_address}."
        )

    if panel or tb:
        location = []
        if panel:
            location.append(f"panel {panel}")
        if tb:
            location.append(f"TB {tb}")
        lines.append(
            "The verified field connection information is "
            + " and ".join(location)
            + "."
        )

    # Never convert absence of evidence into a guessed fault.
    if str(evidence_status).upper() in {
        "NO VERIFIED DATA",
        "NONE",
        "NO DATA",
        "UNKNOWN",
    }:
        lines.append(
            "I don't have verified maintenance evidence that "
            "establishes a specific failure cause for this problem, "
            "so I won't guess."
        )

        lines.append(
            "For a field investigation, verify the instrument and "
            "its signal chain systematically, including the field "
            "condition, instrument power, signal loop, termination "
            "connections and the corresponding PLC input. Compare "
            "the field condition with the PLC/SCADA indication before "
            "concluding that the transmitter itself has failed."
        )
    else:
        lines.append(
            f"Existing V5 maintenance evidence indicates: "
            f"{recommendation_message}"
        )

    if decision:
        lines.append(
            f"V5 decision: {decision}."
        )

    if priority is not None:
        lines.append(
            f"Priority: {priority}."
        )

    if why:
        valid_why = [
            str(x).strip()
            for x in why
            if str(x).strip()
        ]
        if valid_why:
            lines.append(
                "Evidence considered: "
                + " ".join(valid_why)
            )

    lines.append(
        "This is a read-only recommendation. Human verification, "
        "permit requirements, isolation and risk assessment remain "
        "mandatory before field intervention."
    )

    return {
        "answer": " ".join(lines),
        "domain": "troubleshooting",
        "evidence": (
            "verified PCI database + existing V5 maintenance intelligence"
        ),
        "equipment": tag or data.get("equipment"),
        "read_only": True,
        "human_decision_required": True,
        "plc_write": False,
        "scada_control": False,
        "v5_result": data,
    }


def _anvi_troubleshooting_question(question):
    """
    Detect questions asking ANVI to troubleshoot, diagnose or explain
    what to check.

    This does NOT create a new reasoning engine.
    It only changes routing so existing Maintenance/V5 intelligence
    receives priority for troubleshooting intent.
    """
    ql = str(question or "").lower()

    markers = [
        "what should i check",
        "what should we check",
        "what do i check",
        "what do we check",
        "how do i troubleshoot",
        "how should i troubleshoot",
        "how can i troubleshoot",
        "how to troubleshoot",
        "troubleshoot",
        "not working",
        "is not working",
        "isn't working",
        "was not working",
        "wasn't working",
        "failed",
        "failure",
        "fault",
        "faulty",
        "problem with",
        "issue with",
        "what could be wrong",
        "what is wrong",
        "why is it not working",
        "why isn't it working",
        "why did it fail",
        "diagnose",
        "diagnosis",
        "check the instrument",
        "check this instrument",
        "check the transmitter",
        "check this transmitter",
        "repair",
        "fix",
    ]

    return any(x in ql for x in markers)


def ask_anvi(question):
    """
    ANVI conversational intelligence router.

    Existing evidence/V5 systems remain authoritative.
    Conversation context is used to resolve follow-up questions.
    No PLC or SCADA write is performed here.
    """

    q = (question or "").strip()

    if not q:
        return {
            "answer": "Please ask ANVI a question.",
            "domain": "general",
            "read_only": True,
        }

    ql = q.lower()

    try:
        # ============================================================
        # 1. PLANT MEMORY — HIGHEST PRIORITY FOR EXPERIENCE QUESTIONS
        # ============================================================
        if _is_memory_question(q):
            try:
                result = _pci_memory_route(q)
                if result:
                    return result
            except Exception:
                pass

            return {
                "answer": (
                    "I can search ANVIQO Plant Memory for previous "
                    "human field experience, but I could not complete "
                    "that search."
                ),
                "domain": "pci_plant_memory",
                "read_only": True,
            }

        # ============================================================
        # 2. PLANT-WIDE QUESTIONS
        # Do this BEFORE remembered PCI context.
        # ============================================================
        plant_wide_question = any(x in ql for x in [
            "what changed in the plant",
            "what has changed in the plant",
            "plant health",
            "health of the plant",
            "overall plant",
            "plant status",
            "plant condition",
            "plant situation",
            "management summary",
            "executive summary",
            "hod summary",
            "management report",
        ])

        if plant_wide_question:
            if any(x in ql for x in [
                "management",
                "summary",
                "executive",
                "hod",
                "report",
            ]):
                return {
                    "answer": _executive(q),
                    "domain": "executive",
                    "read_only": True,
                    "human_decision_required": True,
                }

            return {
                "answer": _plant(q),
                "domain": "plant",
                "read_only": True,
                "human_decision_required": True,
            }

        # ============================================================
        # 3. EXPLICIT PCI / INSTRUMENT IDENTIFICATION
        # ============================================================
        pci_record = _pci_context_record(q)

        if pci_record:
            _remember_pci_context(record=pci_record)
            return _pci_context_answer(q, pci_record)

        # ============================================================
        # 4. FOLLOW-UP QUESTIONS — REMEMBER LAST PCI INSTRUMENT
        # ============================================================
        previous_pci = _ANVI_CONVERSATION_CONTEXT.get(
            "last_pci_record"
        )

        if previous_pci and _pci_followup_question(q):
            return _pci_context_answer(
                q,
                previous_pci
            )

        # ============================================================
        # 5. PCI SEMANTIC QUESTIONS WITHOUT CURRENT TAG
        # ============================================================
        if _is_pci_question(q):
            import pci_conversation as pc

            result = pc.answer(q)

            if isinstance(result, dict):
                record = result.get("record")

                if isinstance(record, dict):
                    _remember_pci_context(record=record)

                records = result.get("records")

                if isinstance(records, list):
                    _remember_pci_context(results=records)

            return result

        # ============================================================
        # 6. TROUBLESHOOTING / MAINTENANCE
        # ============================================================
        troubleshooting = any(x in ql for x in [
            "troubleshoot",
            "not working",
            "is not working",
            "what should i check",
            "what should we check",
            "what could be wrong",
            "what is wrong",
            "fault",
            "failure",
            "failed",
            "diagnose",
            "diagnosis",
            "repair",
            "maintenance",
            "fix",
            "inspection",
        ])

        if troubleshooting:
            previous = _ANVI_CONVERSATION_CONTEXT.get(
                "last_pci_record"
            )

            if previous:
                tag = str(previous.get("tag", "")).strip()

                if tag:
                    try:
                        answer = _maintenance(
                            f"{q} [{tag}]"
                        )
                    except Exception:
                        answer = _maintenance(q)

                    return {
                        "answer": answer,
                        "domain": "troubleshooting",
                        "read_only": True,
                        "human_decision_required": True,
                        "context_tag": tag,
                    }

            return {
                "answer": _maintenance(q),
                "domain": "maintenance",
                "read_only": True,
                "human_decision_required": True,
            }

        # ============================================================
        # 7. EQUIPMENT — EXISTING V5 PATH
        # ============================================================
        if re.search(
            r"\b(CV|PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|P|FV|XV)[-_]?\d+\b",
            q.upper()
        ):
            return {
                "answer": _equipment(q),
                "domain": "equipment",
                "read_only": True,
            }

        # ============================================================
        # 8. MANAGEMENT / EXECUTIVE
        # ============================================================
        if any(x in ql for x in [
            "management",
            "hod",
            "executive",
            "decision",
            "priority",
            "management report",
        ]):
            return {
                "answer": _executive(q),
                "domain": "executive",
                "read_only": True,
                "human_decision_required": True,
            }

        # ============================================================
        # 9. PLANT / EVENT / HEALTH
        # ============================================================
        if any(x in ql for x in [
            "plant",
            "health",
            "changed",
            "event",
            "events",
            "event chain",
            "situation",
            "condition",
            "status",
            "risk",
        ]):
            return {
                "answer": _plant(q),
                "domain": "plant",
                "read_only": True,
                "human_decision_required": True,
            }

        # ============================================================
        # 10. LLM CONVERSATIONAL FALLBACK
        # ============================================================
        try:
            from anvi_conversation_engine import conversational_answer

            evidence = {
                "system": "ANVIQO",
                "available_intelligence": [
                    "PCI / Instrument Intelligence",
                    "Equipment Intelligence",
                    "Plant Health",
                    "What Changed",
                    "Event Intelligence",
                    "Maintenance Intelligence",
                    "Plant Memory",
                    "Management Intelligence",
                    "Executive Intelligence",
                    "Plant Brain",
                    "V5 Reasoning",
                ],
                "conversation_context": _ANVI_CONVERSATION_CONTEXT,
                "note": (
                    "Existing ANVIQO evidence and V5 intelligence are "
                    "authoritative. Never invent plant facts."
                ),
            }

            result = conversational_answer(
                q,
                evidence=evidence,
                conversation=[],
            )

            if isinstance(result, dict):
                result.setdefault("domain", "conversation")
                result.setdefault("read_only", True)
                result.setdefault(
                    "human_decision_required",
                    True
                )
                return result

        except Exception as conversation_error:
            return {
                "answer": (
                    "ANVI could not start its conversational intelligence "
                    "layer. Existing evidence intelligence remains available. "
                    f"Error: {conversation_error}"
                ),
                "domain": "conversation_error",
                "read_only": True,
            }

        return {
            "answer": (
                "I am ANVI, the conversational intelligence layer "
                "of ANVIQO. I can work with verified plant evidence "
                "and existing V5 intelligence, but I do not have "
                "enough verified evidence to answer that question yet."
            ),
            "domain": "general",
            "read_only": True,
        }

    except Exception as e:
        return {
            "answer": (
                "ANVI could not complete that intelligence request. "
                f"Evidence-layer error: {e}"
            ),
            "domain": "error",
            "read_only": True,
        }

