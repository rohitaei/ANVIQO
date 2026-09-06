from pci_universal_resolver import resolve as _universal_pci_resolve
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
    """
    UNIVERSAL VERIFIED PCI RESOLUTION.

    Resolves:
      1. exact verified tag
      2. verified equipment family
      3. natural-language formatting

    Never invents a tag.
    """
    records = _records()

    rows, mode = _universal_pci_resolve(q, records)

    if not rows:
        return None, None

    return rows[0].get("tag"), rows[0]

def _pci_answer(q):
    ql = q.lower()

    # --------------------------------------------------------
    # NATURAL-LANGUAGE FAMILY + I/O HAS HIGHEST PCI PRIORITY
    #
    # Examples:
    #   what is the DO for MCV 204
    #   show me MCV 204 DO
    #   MCV-204 digital output
    #
    # The universal resolver already proves these records.
    # Do NOT allow generic family resolution to collapse the
    # request to the first record (for example MCV_204_Healthy).
    # --------------------------------------------------------
    try:
        rows, mode = _universal_pci_resolve(q)

        if rows and mode in ("NATURAL_FAMILY_IO", "FAMILY_IO"):
            records = list(rows)

            def _io_name(value):
                return str(value or "").strip().upper()

            io_label = _io_name(records[0].get("io_type", "I/O"))

            lines = [
                f"ANVI found {len(records)} verified {io_label} records for {q.strip()}:"
            ]

            for r in records:
                lines.append(
                    f"{r.get('tag','UNKNOWN')} — "
                    f"{r.get('description','No description')}; "
                    f"PLC: {r.get('plc_address','UNKNOWN')}; "
                    f"Panel: {r.get('panel','UNKNOWN')}; "
                    f"TB: {r.get('tb_name','UNKNOWN')} {r.get('tb_no','')}; "
                    f"Source: {r.get('source_sheet','UNKNOWN')}"
                )

            return {
                "answer": "\n".join(lines),
                "domain": "pci",
                "evidence": "verified PCI database",
                "count": len(records),
                "records": records,
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "human_decision_required": True,
                "context_tag": None,
                "conversation_context": False,
                "match_mode": mode,
            }
    except Exception:
        pass

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
    Build plant-area health evidence from the existing PCI LIVE simulator.

    This is an evidence bridge only:
    - reuses existing PCI LIVE simulation
    - reuses existing plant-health intelligence
    - does not create a second health/prediction engine
    - no PLC write
    - no SCADA control
    """
    from pci_live_simulator import get_live_pci_snapshot

    snapshot = get_live_pci_snapshot() or {}
    pci_areas = snapshot.get("areas", [])

    results = []

    for area in pci_areas:
        if not isinstance(area, dict):
            continue

        score = area.get("health_score")
        if score is None:
            continue

        try:
            score = float(score)
        except (TypeError, ValueError):
            continue

        critical = int(area.get("critical", 0) or 0)
        warning = int(area.get("warning", 0) or 0)
        healthy = int(area.get("healthy", 0) or 0)
        total = int(area.get("total", 0) or 0)

        if score < 40:
            status = "CRITICAL"
        elif score < 60:
            status = "DEGRADED"
        elif score < 80:
            status = "WATCH"
        else:
            status = "HEALTHY"

        results.append({
            "area": area.get("area", "UNKNOWN"),
            "status": status,
            "health_score": round(score, 2),
            "equipment_count": total,
            "critical_equipment": critical,
            "warning_equipment": warning,
            "healthy_equipment": healthy,
            "source": snapshot.get("source", "PCI LIVE"),
            "mode": snapshot.get("mode", "SIMULATION"),
            "evidence": "PCI LIVE area health"
        })

    return results



def _build_unified_plant_evidence_context():
    """
    Unified plant evidence adapter.

    This is an integration/context layer only.
    It does NOT create a new intelligence engine.

    Evidence priority:
        1. Existing PCI Live simulation snapshot
        2. Existing V5 area/equipment health evidence

    Safety:
        - READ ONLY
        - No PLC write
        - No SCADA control
        - No automatic action
    """
    context = {
        "source": [],
        "mode": "READ_ONLY",
        "plant": "PLANT",
        "plant_health_score": None,
        "healthy": 0,
        "warning": 0,
        "critical": 0,
        "changed": 0,
        "active_events": 0,
        "area_count": 0,
        "areas": [],
        "equipment_evidence": [],
        "evidence_available": False,
        "product_boundary": {
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "causation_claim": False,
            "human_decision_required": True,
        },
    }

    # --------------------------------------------------------
    # Existing PCI live evidence
    # --------------------------------------------------------
    try:
        from pci_live_simulator import get_live_pci_snapshot

        snapshot = get_live_pci_snapshot()

        if isinstance(snapshot, dict):
            context["source"].append("PCI_LIVE_SIMULATOR")
            context["mode"] = snapshot.get("mode", "SIMULATION")

            for key in (
                "plant_health_score",
                "healthy",
                "warning",
                "critical",
                "changed",
                "active_events",
                "area_count",
            ):
                if key in snapshot:
                    context[key] = snapshot[key]

            areas = snapshot.get("areas", [])
            if isinstance(areas, list):
                context["areas"] = areas

            if (
                context["plant_health_score"] is not None
                or context["areas"]
                or context["critical"]
                or context["warning"]
            ):
                context["evidence_available"] = True

    except Exception as exc:
        context["pci_live_error"] = str(exc)

    # --------------------------------------------------------
    # Existing V5 equipment/area evidence
    # --------------------------------------------------------
    try:
        equipment_areas = _build_area_results()

        if isinstance(equipment_areas, list):
            context["equipment_evidence"] = equipment_areas

            if not context["areas"]:
                context["areas"] = equipment_areas

            if equipment_areas:
                context["source"].append("V5_AREA_HEALTH")

                if any(
                    isinstance(x, dict)
                    and x.get("health_score") is not None
                    for x in equipment_areas
                ):
                    context["evidence_available"] = True

    except Exception as exc:
        context["area_health_error"] = str(exc)

    return context


def _plant_evidence_answer(q):
    """
    Final unified plant evidence response.

    Separates:
    1. Overall plant health
    2. Risk indicators
    3. Areas requiring investigation

    This is an interpretation/context layer only.
    No new prediction engine is created.
    """

    import json

    evidence = _build_unified_plant_evidence_context()
    ql = q.lower()

    areas = evidence.get("areas", [])
    attention = []

    for area in areas:
        if not isinstance(area, dict):
            continue

        area_name = area.get("area", "UNKNOWN")
        status = str(
            area.get("status", area.get("state", ""))
        ).upper()

        score = area.get("health_score")

        critical = area.get("critical")
        if critical is None:
            critical = area.get("critical_equipment", 0)

        warning = area.get("warning", 0)
        changed = area.get("changed", 0)

        try:
            critical = int(critical or 0)
        except (TypeError, ValueError):
            critical = 0

        try:
            warning = int(warning or 0)
        except (TypeError, ValueError):
            warning = 0

        try:
            changed = int(changed or 0)
        except (TypeError, ValueError):
            changed = 0

        reasons = []

        if critical > 0:
            reasons.append(f"{critical} critical point(s)")

        if warning > 0:
            reasons.append(f"{warning} warning point(s)")

        if changed > 0:
            reasons.append(f"{changed} changed point(s)")

        if status in (
            "CRITICAL",
            "WARNING",
            "EARLY WARNING",
            "DEGRADED",
            "WATCH",
        ):
            reasons.append(f"area status {status}")

        if reasons:
            attention.append({
                "area": area_name,
                "status": status or "ATTENTION",
                "health_score": score,
                "critical_equipment": critical,
                "risk_indicators": reasons,
                "evidence_source": (
                    "PCI LIVE SIMULATION"
                    if "PCI_LIVE_SIMULATOR" in evidence.get("source", [])
                    else "V5 AREA HEALTH"
                ),
            })

    attention.sort(
        key=lambda x: (
            x.get("health_score") is None,
            x.get("health_score")
            if x.get("health_score") is not None
            else 999,
        )
    )

    risk_question = any(x in ql for x in [
        "risk",
        "problem",
        "problems",
        "could develop",
        "may develop",
        "could go wrong",
        "may go wrong",
        "what could happen",
        "potential",
        "future",
        "threat",
    ])

    health_question = any(x in ql for x in [
        "health",
        "status",
        "condition",
        "situation",
        "overall",
    ])

    score = evidence.get("plant_health_score")
    healthy = evidence.get("healthy", 0)
    warning = evidence.get("warning", 0)
    critical = evidence.get("critical", 0)
    changed = evidence.get("changed", 0)
    active_events = evidence.get("active_events", 0)

    try:
        score_num = float(score) if score is not None else None
    except (TypeError, ValueError):
        score_num = None

    if score_num is None:
        health_assessment = "INSUFFICIENT EVIDENCE"
    elif score_num >= 90:
        health_assessment = "BROADLY HEALTHY"
    elif score_num >= 80:
        health_assessment = "HEALTHY WITH ATTENTION AREAS"
    elif score_num >= 60:
        health_assessment = "DEGRADED"
    else:
        health_assessment = "CRITICAL"

    if critical:
        risk_level = "HIGH ATTENTION"
    elif warning or active_events:
        risk_level = "MODERATE ATTENTION"
    elif changed:
        risk_level = "MONITOR"
    else:
        risk_level = "LOW CURRENT INDICATION"

    simulation_mode = (
        "PCI_LIVE_SIMULATOR" in evidence.get("source", [])
        and str(evidence.get("mode", "")).upper() == "SIMULATION"
    )

    response = {
        "question_type": (
            "plant_risk_analysis"
            if risk_question
            else "plant_health_analysis"
            if health_question
            else "plant_situation_analysis"
        ),
        "evidence_status": (
            "EVIDENCE_AVAILABLE"
            if evidence.get("evidence_available")
            else "INSUFFICIENT_EVIDENCE"
        ),
        "evidence_mode": (
            "SIMULATION / DEMO"
            if simulation_mode
            else evidence.get("mode", "READ_ONLY")
        ),
        "plant_health_score": score,
        "health_assessment": health_assessment,
        "risk_level": risk_level,
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "changed": changed,
        "active_events": active_events,
        "area_count": evidence.get("area_count"),
        "areas_requiring_investigation": attention,
        "evidence_sources": evidence.get("source", []),
        "interpretation": (
            f"Overall plant health is {score}/100 and is assessed as "
            f"{health_assessment}. Current risk indicators include "
            f"{critical} critical point(s), {warning} warning point(s), "
            f"{changed} changed point(s), and {active_events} active event(s). "
            f"These indicators identify conditions requiring investigation; "
            f"they do not establish that a specific equipment failure will occur."
            if score is not None
            else
            "ANVI does not have sufficient current plant evidence to establish "
            "overall plant health."
        ),
        "evidence_notice": (
            "CURRENT DATA IS FROM THE PCI LIVE SIMULATOR / DEMO STREAM. "
            "It must not be represented as real plant measurements."
            if simulation_mode
            else
            "Current evidence source is read-only plant intelligence data."
        ),
        "product_boundary": {
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "causation_claim": False,
            "automatic_action": False,
            "human_decision_required": True,
        },
    }

    return (
        "ANVI — Unified Plant Intelligence:\n"
        + json.dumps(response, ensure_ascii=False)
    )


def _plant(q):
    """
    Single plant-wide intelligence entry point.

    All broad plant questions use the same unified evidence context.
    Existing V5 engines remain unchanged.
    """
    return _plant_evidence_answer(q)

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

    # ========================================================
    # V5 DIRECT PLANT MEMORY BRIDGE
    # ========================================================
    # Maintenance recommendation data may not automatically carry
    # verified Plant Memory records. Attach the verified historical
    # records here so every troubleshooting path can use the same
    # authoritative Plant Memory evidence.
    #
    # This does NOT create a new reasoning engine.
    # It only enriches the existing V5 maintenance result.
    # ========================================================
    plant_memory_records = []

    if tag:
        try:
            from plant_memory import search_memory

            plant_memory_records = search_memory(
                tag=tag,
                limit=20
            )

            if not isinstance(plant_memory_records, list):
                plant_memory_records = []

        except Exception:
            plant_memory_records = []

    if isinstance(recommendation, dict):
        recommendation["plant_memory_records"] = (
            plant_memory_records
        )
        recommendation["plant_memory_count"] = (
            len(plant_memory_records)
        )

    # ============================================================
    # VERIFIED PLANT MEMORY -> EXISTING V5 MAINTENANCE BRIDGE
    # ============================================================
    # Plant Memory is historical verified human field experience.
    # It supplements V5 evidence; it does NOT replace or modify the
    # existing V5 maintenance/recommendation engine.
    #
    # Safety:
    #   - no PLC write
    #   - no SCADA control
    #   - no automatic action
    #   - historical evidence is never treated as proof of the
    #     current fault.
    # ============================================================
    verified_memory = []

    try:
        if tag:
            import plant_memory

            # --------------------------------------------------------
            # UNIVERSAL PCI TAG VARIANTS
            # PT_303, PT-303 and PT303 must resolve to the same
            # Plant Memory equipment identity.
            # --------------------------------------------------------
            tag_variants = []

            raw_tag = str(tag or "").strip()

            if raw_tag:
                tag_variants.extend([
                    raw_tag,
                    raw_tag.replace("_", "-"),
                    raw_tag.replace("-", "_"),
                    raw_tag.replace("_", ""),
                    raw_tag.replace("-", ""),
                ])

            # Remove duplicates while preserving order.
            tag_variants = list(dict.fromkeys(
                x for x in tag_variants if x
            ))

            verified_memory = []

            for memory_tag in tag_variants:
                try:
                    matches = plant_memory.search_memory(
                        tag=memory_tag,
                        limit=20
                    )
                except Exception:
                    matches = []

                if isinstance(matches, list):
                    verified_memory.extend(matches)

            # --------------------------------------------------------
            # De-duplicate Plant Memory records by memory_id.
            # --------------------------------------------------------
            unique_memory = {}

            for memory_record in verified_memory:
                if not isinstance(memory_record, dict):
                    continue

                if memory_record.get("verified") is not True:
                    continue

                memory_id = str(
                    memory_record.get("memory_id") or ""
                ).strip()

                if memory_id:
                    unique_memory[memory_id] = memory_record

            verified_memory = list(unique_memory.values())

    except Exception:
        verified_memory = []
    except Exception:
        verified_memory = []

    if isinstance(recommendation, dict):
        recommendation = dict(recommendation)

        # Preserve the authoritative V5 result unchanged while
        # exposing verified historical field evidence separately.
        recommendation["plant_memory_records"] = verified_memory
        recommendation["plant_memory_count"] = len(verified_memory)

    if (
        "recommend" in ql
        or "action" in ql
        or "what should" in ql
        or "maintenance" in ql
        or "repair" in ql
        or "inspection" in ql
        or "fix" in ql
        or "troubleshoot" in ql
        or "diagnose" in ql
        or "diagnosis" in ql
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




def _is_memory_write_command(question):
    """
    Detect explicit conversational requests to remember/store
    maintenance history.

    This is intentionally narrow so ordinary questions do not
    accidentally create Plant Memory.
    """
    ql = str(question or "").strip().lower()

    return any(x in ql for x in [
        "remember this maintenance history",
        "remember this maintenance",
        "remember this history",
        "remember this for",
        "remember the maintenance history",
        "save this maintenance history",
        "save this maintenance",
        "store this maintenance history",
        "store this maintenance",
        "record this maintenance history",
        "record this maintenance",
        "add this to plant memory",
        "save this to plant memory",
        "remember in plant memory",
    ])


def _extract_memory_write(question):
    """
    Deterministic parser for conversational maintenance history.

    Returns a structured record or None.
    """
    q = str(question or "").strip()

    if not _is_memory_write_command(q):
        return None

    # ------------------------------------------------------------
    # TAG
    # ------------------------------------------------------------
    tag_match = re.search(
        r"(?:for|on|about)\s+([A-Za-z]{1,8}[-_ ]?\d{1,5})\s*:",
        q,
        re.I
    )

    if not tag_match:
        tag_match = re.search(
            r"\b([A-Za-z]{1,8}[-_ ]?\d{1,5})\b",
            q,
            re.I
        )

    if not tag_match:
        return None

    raw_tag = tag_match.group(1).strip().upper()
    tag = re.sub(r"[\s_]+", "-", raw_tag)

    # ------------------------------------------------------------
    # History text
    # ------------------------------------------------------------
    history = q[tag_match.end():].strip()

    if history.startswith(":"):
        history = history[1:].strip()

    # Remove surrounding quotation marks.
    history = history.strip().strip('"').strip("'").strip()

    # ------------------------------------------------------------
    # Deterministic field extraction
    # ------------------------------------------------------------
    observation = ""
    finding = ""
    maintenance_action = ""
    confirmation_evidence = ""
    outcome = ""
    recovery_status = ""
    spare_used = ""

    if re.search(r"pressure indication was abnormal", history, re.I):
        observation = "Pressure indication abnormal"
        event = f"{tag} abnormal pressure indication"
    else:
        event = f"Maintenance history for {tag}"

    m = re.search(
        r"(?:transmitter was|transmitter found|found)\s+faulty",
        history,
        re.I
    )
    if m:
        finding = "Transmitter found faulty"

    if re.search(
        r"(?:replaced|replace)\s+(?:the\s+)?transmitter",
        history,
        re.I
    ):
        maintenance_action = "Replaced transmitter"

    if re.search(
        r"signal returned healthy|signal was healthy|returned healthy",
        history,
        re.I
    ):
        confirmation_evidence = "Signal returned healthy"
        outcome = "Healthy signal restored"
        recovery_status = "Recovered"

    spare_match = re.search(
        r"(?:used|use)\s+(\d+)\s+([A-Za-z]{1,8}[-_ ]?\d{1,5})\s+spare",
        history,
        re.I
    )

    if spare_match:
        qty = int(spare_match.group(1))
        spare_tag = re.sub(
            r"[\s_]+",
            "-",
            spare_match.group(2).strip().upper()
        )
        spare_used = f"{spare_tag} x{qty}"

    # ------------------------------------------------------------
    # Engineering context may be included after the history.
    # ------------------------------------------------------------
    equipment = "Pressure Transmitter" if (
        "transmitter" in history.lower()
    ) else ""

    area = ""
    engineering_description = ""

    context_match = re.search(
        rf"{re.escape(tag)}\s+is\s+([^\.]+)",
        q,
        re.I
    )

    if context_match:
        engineering_description = context_match.group(1).strip()

        area_match = re.search(
            r"\bin\s+([A-Za-z0-9 &/_-]+?)(?:\.|Verified field information:|$)",
            engineering_description,
            re.I
        )

        if area_match:
            area = area_match.group(1).strip()

    # ------------------------------------------------------------
    # Additional field information
    # ------------------------------------------------------------
    io_type = ""
    plc_address = ""
    panel = ""
    tb = ""
    terminals = ""

    m = re.search(r"I/O:\s*([^;.\n]+)", q, re.I)
    if m:
        io_type = m.group(1).strip()

    m = re.search(r"PLC address:\s*([^;.\n]+)", q, re.I)
    if m:
        plc_address = m.group(1).strip()

    m = re.search(r"Panel:\s*([^;.\n]+)", q, re.I)
    if m:
        panel = m.group(1).strip()

    m = re.search(r"TB:\s*([^;.\n]+)", q, re.I)
    if m:
        tb = m.group(1).strip()

    m = re.search(r"Terminals:\s*([^;.\n]+)", q, re.I)
    if m:
        terminals = m.group(1).strip()

    safety_note = ""
    if "read-only" in q.lower():
        safety_note = (
            "Read-only maintenance guidance. Human verification, "
            "permit requirements, isolation and risk assessment "
            "remain mandatory before field intervention."
        )

    notes = "; ".join(
        x for x in [
            f"Engineering description: {engineering_description}" if engineering_description else "",
            f"I/O: {io_type}" if io_type else "",
            f"PLC address: {plc_address}" if plc_address else "",
            f"Panel: {panel}" if panel else "",
            f"TB: {tb}" if tb else "",
            f"Terminals: {terminals}" if terminals else "",
            safety_note,
        ]
        if x
    )

    return {
        "event": event,
        "source": "conversational maintenance history",
        "equipment": equipment,
        "tag": tag,
        "area": area,
        "observation": observation,
        "maintenance_action": maintenance_action,
        "finding": finding,
        "confirmation_evidence": confirmation_evidence,
        "outcome": outcome,
        "recovery_status": recovery_status,
        "spare_used": spare_used,
        "notes": notes,
    }


def _plant_memory_write_route(question):
    """
    Explicit conversational Plant Memory write.

    No PLC write.
    No SCADA control.
    User-supplied history remains pending human verification.
    """
    record_data = _extract_memory_write(question)

    if not record_data:
        return None

    try:
        import plant_memory

        record = plant_memory.create_conversational_memory(
            **record_data
        )

        verified = record.get("verified") is True
        verification_status = (
            "VERIFIED" if verified else "PENDING_VERIFICATION"
        )

        if verified:
            answer = (
                f"ANVI already has this maintenance history stored for "
                f"{record.get('tag')}.\\n"
                f"Event: {record.get('event') or 'Maintenance history'}\\n"
                f"Finding: {record.get('finding') or 'Not explicitly stated'}\\n"
                f"Action: {record.get('maintenance_action') or 'Not explicitly stated'}\\n"
                f"Outcome: {record.get('outcome') or 'Not explicitly stated'}\\n"
                f"Recovery status: {record.get('recovery_status') or 'Not explicitly stated'}\\n"
                f"Spare used: {record.get('spare_used') or 'None stated'}\\n"
                f"Memory ID: {record.get('memory_id')}\\n"
                f"Verification status: VERIFIED\\n"
                f"No duplicate Plant Memory record was created."
            )
        else:
            answer = (
                f"ANVI remembered the maintenance history for "
                f"{record.get('tag')}.\\n"
                f"Event: {record.get('event') or 'Maintenance history'}\\n"
                f"Finding: {record.get('finding') or 'Not explicitly stated'}\\n"
                f"Action: {record.get('maintenance_action') or 'Not explicitly stated'}\\n"
                f"Outcome: {record.get('outcome') or 'Not explicitly stated'}\\n"
                f"Recovery status: {record.get('recovery_status') or 'Not explicitly stated'}\\n"
                f"Spare used: {record.get('spare_used') or 'None stated'}\\n"
                f"Memory ID: {record.get('memory_id')}\\n"
                f"Verification status: PENDING_VERIFICATION\\n"
                f"This is stored user-provided history, not verified evidence."
            )

        return {
            "answer": answer,
            "domain": "plant_memory",
            "evidence": "conversational maintenance history",
            "memory_id": record.get("memory_id"),
            "tag": record.get("tag"),
            "record": record,
            "verification_status": verification_status,
            "verified": verified,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_verification_required": True,
            "human_decision_required": True,
        }

    except Exception as e:
        return {
            "answer": (
                "ANVI could not store the maintenance history. "
                "No plant-history claim has been made."
            ),
            "domain": "plant_memory",
            "evidence": "plant memory write error",
            "error": str(e),
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_verification_required": True,
        }



def _pci_memory_route(question):
    """
    ANVIQO Plant Memory / Verified Action Recall bridge.

    Uses the current plant_memory.py structured memory store.

    Important:
      - Verified memories may be recalled as evidence.
      - Unverified memories are never presented as proven facts.
      - This layer performs retrieval only.
      - No PLC/SCADA write is performed.
    """

    q = str(question or "").strip()
    ql = q.lower()

    memory_question = _is_memory_question(q)

    if not memory_question:
        return None

    # ------------------------------------------------------------
    # Resolve the engineering tag from the verified PCI registry.
    # Normalized questions may contain PT_303 while the memory
    # record uses PT-303. Resolve both forms.
    # ------------------------------------------------------------

    tag = None

    try:
        from pci_registry import search

        registry = search(
            query=None,
            limit=1064
        )

        normalized_q = re.sub(
            r"[\s_-]+",
            "_",
            q.upper()
        )

        for item in registry:
            candidate = str(
                item.get("tag", "")
            ).strip()

            if not candidate:
                continue

            candidates = {
                candidate.upper(),
                candidate.upper().replace("-", "_"),
                candidate.upper().replace("_", "-"),
            }

            if any(
                c in normalized_q
                for c in candidates
            ):
                tag = candidate
                break

    except Exception:
        pass

    # ------------------------------------------------------------
    # Search CURRENT Plant Memory.
    # Do NOT use the legacy pci_plant_memory.py database here.
    # ------------------------------------------------------------

    try:
        import plant_memory

        results = plant_memory.search_all_memory(
            query=q,
            tag=tag or "",
            limit=20
        )

    except Exception as e:
        return {
            "answer": (
                "ANVI could not access the current Plant Memory "
                "service. No plant-history claim has been made."
            ),
            "domain": "plant_memory",
            "evidence": "plant memory service error",
            "tag": tag,
            "error": str(e),
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_verification_required": True,
        }

    if not isinstance(results, list):
        results = []

    # ------------------------------------------------------------
    # Structured fallback:
    #
    # A natural-language action question may have no keyword
    # overlap with the original event description.
    #
    # Example:
    #   "What action fixed PT-303 previously?"
    #
    # The memory record itself contains:
    #   maintenance_action
    #   finding
    #   confirmation_evidence
    #   outcome
    #
    # Therefore, when a tag is known, retrieve by tag rather than
    # requiring lexical similarity.
    # ------------------------------------------------------------

    if not results and tag:

        try:
            results = plant_memory.search_all_memory(
                query="",
                tag=tag,
                limit=20
            )
        except Exception:
            results = []

    # ------------------------------------------------------------
    # Normalize PT_303 <-> PT-303 matching if direct tag search
    # did not return anything.
    # ------------------------------------------------------------

    if not results and tag:

        tag_variants = {
            tag.lower(),
            tag.lower().replace("-", "_"),
            tag.lower().replace("_", "-"),
        }

        try:
            all_results = plant_memory.search_all_memory(
                query="",
                limit=100
            )

            for record in all_results:
                record_tag = str(
                    record.get("tag", "")
                ).strip().lower()

                if (
                    record_tag in tag_variants
                    or record_tag.replace("-", "_")
                    in {
                        x.replace("-", "_")
                        for x in tag_variants
                    }
                ):
                    results.append(record)

        except Exception:
            pass

    # ------------------------------------------------------------
    # No memory found.
    # ------------------------------------------------------------

    if not results:
        return {
            "answer": (
                f"I could not find verified Plant Memory evidence"
                + (f" for {tag}." if tag else ".")
                + " I will not invent plant history or recommend "
                  "an action without supporting evidence."
            ),
            "domain": "plant_memory",
            "evidence": "plant memory",
            "count": 0,
            "tag": tag,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_verification_required": True,
        }

    # ------------------------------------------------------------
    # Only VERIFIED records may be used for Verified Action Recall.
    # ------------------------------------------------------------

    verified = [
        r for r in results
        if r.get("verified") is True
    ]

    if not verified:
        first_pending = results[0] if results else {}

        answer_lines = [
            (
                f"ANVI found {len(results)} pending Plant Memory "
                f"record(s)"
                + (f" for {tag}." if tag else ".")
            ),
            "This history was provided conversationally and is NOT verified.",
        ]

        if first_pending.get("event"):
            answer_lines.append(
                "Event: " + str(first_pending["event"])
            )

        if first_pending.get("observation"):
            answer_lines.append(
                "Observation: " + str(first_pending["observation"])
            )

        if first_pending.get("finding"):
            answer_lines.append(
                "Finding: " + str(first_pending["finding"])
            )

        if first_pending.get("maintenance_action"):
            answer_lines.append(
                "Action: " + str(first_pending["maintenance_action"])
            )

        if first_pending.get("confirmation_evidence"):
            answer_lines.append(
                "Confirmation evidence: "
                + str(first_pending["confirmation_evidence"])
            )

        if first_pending.get("outcome"):
            answer_lines.append(
                "Outcome: " + str(first_pending["outcome"])
            )

        if first_pending.get("recovery_status"):
            answer_lines.append(
                "Recovery status: "
                + str(first_pending["recovery_status"])
            )

        if first_pending.get("spare_used"):
            answer_lines.append(
                "Spare used: " + str(first_pending["spare_used"])
            )

        if first_pending.get("memory_id"):
            answer_lines.append(
                "Memory ID: " + str(first_pending["memory_id"])
            )

        answer_lines.append(
            "Verification status: PENDING_VERIFICATION"
        )
        answer_lines.append(
            "ANVI will not present this previous history as proven "
            "maintenance evidence until it is verified."
        )

        return {
            "answer": "\n".join(answer_lines),
            "domain": "plant_memory",
            "evidence": "pending conversational plant memory",
            "count": len(results),
            "tag": tag,
            "reports": results,
            "verification_status": "PENDING_VERIFICATION",
            "verified": False,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_verification_required": True,
            "human_decision_required": True,
        }

    # ------------------------------------------------------------
    # Comprehensive verified context recall.
    #
    # Example:
    #   "Tell me everything you remember about PT-303"
    #
    # Combine the current PCI engineering identity with verified
    # Plant Memory. This is still retrieval-only and read-only.
    # ------------------------------------------------------------

    comprehensive_intent = any(x in ql for x in [
        "everything you remember",
        "everything you know about",
        "tell me everything you remember",
        "tell me everything about",
        "what do you remember about",
        "what do we remember about",
        "all previous experience",
        "all previous history",
    ])

    if comprehensive_intent:
        first = verified[0]

        # Resolve the current PCI engineering record for the same tag.
        pci_record = None

        try:
            from pci_registry import search

            registry = search(query=None, limit=1064)

            target_tag = str(first.get("tag") or tag or "").strip().upper()
            target_norm = target_tag.replace("-", "_")

            for item in registry:
                item_tag = str(item.get("tag", "")).strip().upper()
                item_norm = item_tag.replace("-", "_")

                if item_tag == target_tag or item_norm == target_norm:
                    pci_record = item
                    break

        except Exception:
            pci_record = None

        answer_lines = []

        answer_lines.append(
            "ANVI — Complete verified context for "
            + str(first.get("tag") or tag or "this equipment")
            + "."
        )

        # -------------------------
        # Engineering identity
        # -------------------------
        if pci_record:
            answer_lines.append("")
            answer_lines.append("ENGINEERING IDENTITY:")

            engineering_fields = [
                ("Description", [
                    "description",
                    "instrument_description",
                    "service",
                    "location",
                ]),
                ("Area", ["area"]),
                ("I/O type", ["io_type", "i/o_type", "io"]),
                ("PLC address", ["plc_address", "address"]),
                ("Panel", ["panel"]),
                ("TB", ["tb", "terminal_block"]),
                ("Source", ["source", "source_document"]),
            ]

            for label, keys in engineering_fields:
                value = ""
                for key in keys:
                    candidate = pci_record.get(key)
                    if candidate not in (None, ""):
                        value = str(candidate).strip()
                        break

                if value:
                    answer_lines.append(f"{label}: {value}")

        # -------------------------
        # Verified Plant Memory
        # -------------------------
        answer_lines.append("")
        answer_lines.append("VERIFIED PLANT MEMORY:")

        event = str(first.get("event", "")).strip()
        finding = str(first.get("finding", "")).strip()
        action = str(first.get("maintenance_action", "")).strip()
        outcome = str(first.get("outcome", "")).strip()
        evidence = str(first.get("confirmation_evidence", "")).strip()
        recovery = str(first.get("recovery_status", "")).strip()
        spare = str(first.get("spare_used", "")).strip()

        if event:
            answer_lines.append("Previous event: " + event)

        if finding:
            answer_lines.append("Finding: " + finding)

        if action:
            answer_lines.append("Action: " + action)

        if outcome:
            answer_lines.append("Outcome: " + outcome)

        if evidence:
            answer_lines.append("Confirmation evidence: " + evidence)

        if recovery:
            answer_lines.append("Recovery status: " + recovery)

        if spare:
            answer_lines.append("Spare used: " + spare)

        if first.get("memory_id"):
            answer_lines.append("Memory ID: " + str(first["memory_id"]))

        answer_lines.append("Verification status: VERIFIED")
        answer_lines.append("")
        answer_lines.append(
            "This history is verified human field experience, "
            "not an automatic maintenance command."
        )

        return {
            "answer": "\n".join(answer_lines),
            "domain": "plant_memory",
            "evidence": "verified PCI database + verified plant memory",
            "tag": first.get("tag") or tag,
            "pci_record": pci_record,
            "plant_memory_records": verified,
            "plant_memory_count": len(verified),
            "memory_id": first.get("memory_id"),
            "verification_status": "VERIFIED",
            "verified": True,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_decision_required": True,
        }

    # ------------------------------------------------------------
    # Specific verified recovery-status recall.
    #
    # Examples:
    #   "Was PT-303 recovered?"
    #   "Was PT-303 recovered after the previous failure?"
    #   "What is the recovery status of PT-303?"
    # ------------------------------------------------------------

    recovery_intent = any(x in ql for x in [
        "was recovered",
        "were recovered",
        "recovered after",
        "recovered previously",
        "was it recovered",
        "did it recover",
        "did we recover",
        "recovery status",
        "was restored",
        "were restored",
    ])

    # Robust recovery-question detection, including:
    # "Was PT-303 recovered?"
    # "Was PT-303 recovered after the previous failure?"
    # "Is PT-303 recovered?"
    if re.search(r"\bwas\b.{0,100}\brecovered\b", ql):
        recovery_intent = True

    if re.search(r"\b(is|was)\b.{0,100}\b(recovered|restored)\b", ql):
        recovery_intent = True


    if recovery_intent:
        first = verified[0]

        recovery = str(
            first.get("recovery_status", "")
        ).strip()

        outcome = str(
            first.get("outcome", "")
        ).strip()

        evidence = str(
            first.get("confirmation_evidence", "")
        ).strip()

        event = str(
            first.get("event", "")
        ).strip()

        if recovery:
            recovery_status = recovery
        elif outcome:
            recovery_status = "Recovered" if any(
                x in outcome.lower()
                for x in [
                    "healthy signal restored",
                    "restored",
                    "recovered",
                    "returned healthy",
                ]
            ) else "Not recorded."
        else:
            recovery_status = "Not recorded."

        answer_lines = [
            "ANVI found verified previous maintenance experience"
            + (
                f" for {first.get('tag') or tag}."
                if (first.get('tag') or tag)
                else "."
            ),
        ]

        if event:
            answer_lines.append("Previous event: " + event)

        answer_lines.append("Recovery status: " + recovery_status)

        if outcome:
            answer_lines.append("Outcome: " + outcome)

        if evidence:
            answer_lines.append("Confirmation evidence: " + evidence)

        if first.get("memory_id"):
            answer_lines.append(
                "Memory: " + str(first["memory_id"])
            )

        answer_lines.append("Verification status: VERIFIED")
        answer_lines.append(
            "This is verified maintenance experience, not an "
            "automatic maintenance command."
        )

        return {
            "answer": "\n".join(answer_lines),
            "domain": "plant_memory",
            "evidence": "verified plant memory",
            "tag": first.get("tag") or tag,
            "memory_id": first.get("memory_id"),
            "recovery_status": recovery_status,
            "outcome": first.get("outcome"),
            "confirmation_evidence": first.get(
                "confirmation_evidence"
            ),
            "verification_status": "VERIFIED",
            "records": verified,
            "count": len(verified),
            "verified": True,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_decision_required": True,
        }

    # ------------------------------------------------------------
    # Specific verified spare-use recall.
    #
    # Examples:
    #   "Did we use a spare for PT-303 previously?"
    #   "Was a spare used for PT-303?"
    # ------------------------------------------------------------

    spare_intent = any(x in ql for x in [
        "did we use a spare",
        "did we use spare",
        "was a spare used",
        "was spare used",
        "used a spare",
        "used spare",
        "spare used",
        "previous spare",
        "previously use a spare",
        "previously used a spare",
        "did we replace it with a spare",
        "was it replaced with a spare",
    ])

    if spare_intent:
        first = verified[0]

        spare = str(
            first.get("spare_used", "")
        ).strip()

        if spare:
            spare_text = spare
            spare_statement = "Spare used: " + spare_text
        else:
            spare_statement = "Spare used: No verified spare usage recorded."

        event = str(
            first.get("event", "")
        ).strip()

        action = str(
            first.get("maintenance_action", "")
        ).strip()

        answer_lines = [
            "ANVI found verified previous maintenance experience"
            + (
                f" for {first.get('tag') or tag}."
                if (first.get('tag') or tag)
                else "."
            ),
        ]

        if event:
            answer_lines.append("Previous event: " + event)

        answer_lines.append(spare_statement)

        if action:
            answer_lines.append("Action: " + action)

        if first.get("memory_id"):
            answer_lines.append(
                "Memory: " + str(first["memory_id"])
            )

        answer_lines.append("Verification status: VERIFIED")
        answer_lines.append(
            "This is verified maintenance experience, not an "
            "automatic maintenance command."
        )

        return {
            "answer": "\n".join(answer_lines),
            "domain": "plant_memory",
            "evidence": "verified plant memory",
            "tag": first.get("tag") or tag,
            "memory_id": first.get("memory_id"),
            "spare_used": spare,
            "maintenance_action": first.get(
                "maintenance_action"
            ),
            "verification_status": "VERIFIED",
            "records": verified,
            "count": len(verified),
            "verified": True,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "human_decision_required": True,
        }

    # ------------------------------------------------------------
    # Determine whether the user is asking specifically for the
    # previous corrective action / what worked.
    # ------------------------------------------------------------

    action_intent = any(x in ql for x in [
        "what action fixed",
        "what action solved",
        "what fixed",
        "what solved",
        "what worked before",
        "what worked previously",
        "what did we do before",
        "what did we do last time",
        "previous action",
        "previous repair",
        "previous solution",
        "previous fix",
        "how was it fixed",
        "how did we fix",
        "how was this fixed",
    ])

    if action_intent:

        recalled = []

        for r in verified:

            action = str(
                r.get("maintenance_action", "")
            ).strip()

            finding = str(
                r.get("finding", "")
            ).strip()

            evidence = str(
                r.get("confirmation_evidence", "")
            ).strip()

            outcome = str(
                r.get("outcome", "")
            ).strip()

            if not action:
                continue

            recalled.append({
                "memory_id": r.get("memory_id"),
                "tag": r.get("tag") or tag,
                "event": r.get("event", ""),
                "finding": finding,
                "maintenance_action": action,
                "confirmation_evidence": evidence,
                "outcome": outcome,
                "verification_status": "VERIFIED",
            })

        if recalled:

            first = recalled[0]

            answer = (
                "ANVI found verified previous maintenance experience"
                + (
                    f" for {first.get('tag')}."
                    if first.get("tag")
                    else "."
                )
                + "\n\n"
                + "Previous action: "
                + first["maintenance_action"]
                + "\n"
                + "Finding: "
                + (first["finding"] or "Not recorded.")
                + "\n"
                + "Outcome: "
                + (first["outcome"] or "Not recorded.")
                + "\n"
                + "Confirmation evidence: "
                + (
                    first["confirmation_evidence"]
                    or "Not recorded."
                )
                + "\n\n"
                + "This is verified maintenance experience, "
                  "not an automatic maintenance command."
            )

            return {
                "answer": answer,
                "domain": "verified_action_recall",
                "evidence": "verified plant memory",
                "tag": first.get("tag") or tag,
                "memory_id": first.get("memory_id"),
                "finding": first.get("finding"),
                "maintenance_action": first.get(
                    "maintenance_action"
                ),
                "outcome": first.get("outcome"),
                "confirmation_evidence": first.get(
                    "confirmation_evidence"
                ),
                "verification_status": "VERIFIED",
                "records": recalled,
                "count": len(recalled),
                "verified": True,
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
                "human_decision_required": True,
            }

    # ------------------------------------------------------------
    # General previous-experience recall.
    #
    # Show the actual verified experience instead of only reporting
    # that a memory record exists.
    # ------------------------------------------------------------

    first = verified[0]

    event = str(
        first.get("event", "")
    ).strip()

    finding = str(
        first.get("finding", "")
    ).strip()

    action = str(
        first.get("maintenance_action", "")
    ).strip()

    outcome = str(
        first.get("outcome", "")
    ).strip()

    evidence = str(
        first.get("confirmation_evidence", "")
    ).strip()

    answer_lines = [
        "Yes — ANVI found "
        + str(len(verified))
        + " verified previous human field experience "
          "record(s)"
        + (f" for {first.get('tag') or tag}." if (first.get("tag") or tag) else ".")
    ]

    if event:
        answer_lines.append("Previous event: " + event)

    if finding:
        answer_lines.append("Finding: " + finding)

    if action:
        answer_lines.append("Action: " + action)

    if outcome:
        answer_lines.append("Outcome: " + outcome)

    if evidence:
        answer_lines.append("Evidence: " + evidence)

    if first.get("memory_id"):
        answer_lines.append("Memory: " + str(first["memory_id"]))

    answer_lines.append("Status: VERIFIED")
    answer_lines.append(
        "This is verified maintenance experience, not an "
        "automatic maintenance command."
    )

    return {
        "answer": "\n".join(answer_lines),
        "domain": "plant_memory",
        "evidence": "verified plant memory",
        "count": len(verified),
        "tag": tag,
        "reports": verified,
        "verification_status": "VERIFIED",
        "verified": True,
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
    """
    Detect Plant Memory / previous human experience questions.

    IMPORTANT:
    A verified PCI tag inside the question must NOT prevent memory
    retrieval. The tag is used as context for the memory search.
    """
    ql = str(q or "").lower()

    # Semantic recovery questions may contain the equipment tag
    # between the subject and the recovery word.
    # Example: "Was PT-303 recovered?"
    if re.search(r"\bwas\b.{0,80}\brecovered\b", ql):
        return True

    if re.search(r"\b(recovery status|recovered after|recovered previously)\b", ql):
        return True

    return any(x in ql for x in [
        "have we seen this before",
        "have we seen",
        "seen this before",
        "seen this pattern before",
        "seen this problem before",
        "seen this issue before",
        "seen this failure before",
        "previous experience",
        "past experience",
        "previous report",
        "past report",
        "previous problem",
        "past problem",
        "previous issue",
        "past issue",
        "previous failure",
        "past failure",
        "previous action",
        "previous repair",
        "previous solution",
        "previous fix",
        "previously",
        "last time",
        "earlier experience",
        "earlier problem",
        "earlier issue",
        "what happened before",
        "what did we do before",
        "what did we do last time",
        "what action fixed",
        "what action solved",
        "what fixed",
        "what solved",
        "what worked before",
        "what worked previously",
        "how was it fixed",
        "how did we fix",
        "how was this fixed",
        "similar problem",
        "similar issue",
        "similar failure",
        "similar event",
        "history of this problem",
        "history of this issue",
        "plant memory",
        "previous maintenance",
        "past maintenance",

        # Recovery / outcome recall
        "was recovered",
        "were recovered",
        "recovered after",
        "recovered previously",
        "was it recovered",
        "did it recover",
        "did we recover",
        "recovery status",
        "was restored",
        "were restored",

        # Spare-use / replacement recall
        "did we use a spare",
        "did we use spare",
        "was a spare used",
        "was spare used",
        "used a spare",
        "used spare",
        "spare used",
        "previous spare",
        "previously use a spare",
        "previously used a spare",
        "did we replace it with a spare",
        "was it replaced with a spare",

        # Finding / discovery recall
        "what was the finding",
        "what was the fault",
        "what was found",
        "what did we find",
        "what did the technician find",
        "what did maintenance find",
        "what was discovered",
        "what was the issue found",
        "what was wrong previously",

        # Comprehensive Plant Memory recall
        "everything you remember",
        "everything you know about",
        "tell me everything you remember",
        "tell me everything about",
        "what do you remember about",
        "what do we remember about",
        "all previous experience",
        "all previous history",
    ])


def _is_pci_question(q):
    # Explicit troubleshooting must never be downgraded to
    # a generic PCI information lookup.
    if _is_troubleshooting_question(q):
        return False

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


def _anvi_memory_tag_variants(tag):
    """
    Return equivalent tag forms used across ANVIQO data sources.

    PCI/V5 commonly uses PT_303 while Plant Memory may use PT-303.
    Memory search is normalized here so the underlying databases remain
    unchanged.
    """
    raw = str(tag or "").strip()

    if not raw:
        return []

    variants = []
    for value in (
        raw,
        raw.replace("_", "-"),
        raw.replace("-", "_"),
    ):
        value = value.strip()
        if value and value not in variants:
            variants.append(value)

    return variants


def _anvi_search_memory_for_tag(tag="", equipment="", area="", query="",
                                limit=20):
    """
    Search Plant Memory for troubleshooting context.

    This bridge intentionally uses search_all_memory() because a
    conversationally supplied history can be useful as a historical clue,
    but its verification status must remain visible to the caller.

    Normal memory recall continues to use verified-only search_memory().
    """
    from plant_memory import search_all_memory

    variants = _anvi_memory_tag_variants(tag)

    results = []
    seen = set()

    if not variants:
        variants = [""]

    for variant in variants:
        rows = search_all_memory(
            query=query,
            tag=variant,
            equipment=equipment,
            area=area,
            limit=limit
        )

        for row in rows:
            if not isinstance(row, dict):
                continue

            memory_id = row.get("memory_id")

            if memory_id in seen:
                continue

            seen.add(memory_id)
            results.append(row)

            if len(results) >= limit:
                return results

    return results


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
    Convert existing V5 maintenance intelligence into a technician-friendly
    conversational response.

    Rules:
    - Never invent maintenance history.
    - Preserve V5 evidence and uncertainty.
    - Use verified PCI context when available.
    - Read-only guidance only.
    """

    data = maintenance_result if isinstance(maintenance_result, dict) else {}

    # ------------------------------------------------------------
    # DIRECT VERIFIED PLANT MEMORY LOOKUP — FINAL BRIDGE
    # ------------------------------------------------------------
    # Plant Memory stores canonical instrument tags such as PT-303,
    # while PCI/V5 commonly uses PT_303.
    #
    # Do NOT depend on conversation context or an intermediate bridge.
    # Troubleshooting already has the resolved PCI equipment tag.
    #
    # Search both canonical forms directly in the authoritative
    # Plant Memory database. Only verified=True records are returned
    # by plant_memory.search_memory().
    # ------------------------------------------------------------
    direct_memory_records = []

    try:
        from plant_memory import search_memory

        bridge_tag = str(
            data.get("equipment")
            or ""
        ).strip()

        if not bridge_tag and isinstance(pci_record, dict):
            bridge_tag = str(
                pci_record.get("tag")
                or pci_record.get("instrument_tag")
                or pci_record.get("name")
                or ""
            ).strip()

        if bridge_tag:
            tag_variants = []

            for candidate in (
                bridge_tag,
                bridge_tag.replace("_", "-"),
                bridge_tag.replace("-", "_"),
                bridge_tag.replace(" ", "-"),
                bridge_tag.replace(" ", "_"),
            ):
                candidate = str(candidate or "").strip()

                if candidate and candidate.lower() not in {
                    x.lower() for x in tag_variants
                }:
                    tag_variants.append(candidate)

            found = {}

            for candidate in tag_variants:
                try:
                    records = search_memory(
                        tag=candidate,
                        limit=20
                    )

                    if isinstance(records, list):
                        for memory in records:
                            if not isinstance(memory, dict):
                                continue

                            if memory.get("verified") is not True:
                                continue

                            mid = memory.get("memory_id")

                            if mid:
                                found[mid] = memory
                except Exception:
                    continue

            direct_memory_records = list(found.values())

    except Exception:
        direct_memory_records = []

    # Merge direct verified memory into the V5 recommendation result.
    existing = recommendation_records = data.get(
        "plant_memory_records"
    )

    if not isinstance(existing, list):
        existing = []

    known_ids = {
        x.get("memory_id")
        for x in existing
        if isinstance(x, dict)
    }

    for memory in direct_memory_records:
        mid = memory.get("memory_id")

        if mid and mid not in known_ids:
            existing.append(memory)
            known_ids.add(mid)

    if existing:
        data["plant_memory_records"] = existing
        data["plant_memory_count"] = len(existing)



    record = pci_record
    if not isinstance(record, dict):
        record = _ANVI_CONVERSATION_CONTEXT.get("last_pci_record")

    tag = ""
    description = ""
    area = ""
    plc = ""
    panel = ""
    tb = ""
    terminals = ""
    io_type = ""

    if isinstance(record, dict):
        tag = str(
            record.get("tag")
            or record.get("instrument_tag")
            or record.get("name")
            or ""
        ).strip()

        description = str(
            record.get("description")
            or record.get("instrument")
            or record.get("title")
            or ""
        ).strip()

        area = str(
            record.get("area")
            or record.get("location")
            or ""
        ).strip()

        plc = str(
            record.get("plc_address")
            or record.get("plc")
            or record.get("address")
            or ""
        ).strip()

        panel = str(record.get("panel") or "").strip()

        tb = str(
            record.get("tb")
            or record.get("terminal_block")
            or record.get("tb_name")
            or ""
        ).strip()

        terminals = str(
            record.get("terminal")
            or record.get("terminals")
            or record.get("terminal_reference")
            or record.get("tb_no")
            or ""
        ).strip()

        io_type = str(record.get("io_type") or "").strip()

    equipment = str(
        data.get("equipment")
        or tag
        or "the instrument"
    ).strip()

    recommendation = data.get("recommendation")
    if not isinstance(recommendation, dict):
        recommendation = {}

    # --------------------------------------------------------
    # V5 -> PLANT MEMORY BRIDGE
    # --------------------------------------------------------
    # Existing V5 maintenance intelligence may already contain
    # verified Plant Memory records. Preserve them in the
    # conversational response instead of dropping them.
    plant_memory_records = recommendation.get(
        "plant_memory_records"
    )

    if not isinstance(plant_memory_records, list):
        plant_memory_records = data.get("plant_memory_records", [])

    if not isinstance(plant_memory_records, list):
        plant_memory_records = []

    plant_memory_count = recommendation.get(
        "plant_memory_count"
    )

    if plant_memory_count is None:
        plant_memory_count = data.get(
            "plant_memory_count",
            len(plant_memory_records)
        )

    try:
        plant_memory_count = int(plant_memory_count)
    except Exception:
        plant_memory_count = len(plant_memory_records)

    message = str(
        recommendation.get("message")
        or data.get("recommendation")
        or ""
    ).strip()

    evidence_status = str(
        recommendation.get("evidence_status")
        or data.get("evidence_status")
        or ""
    ).strip()

    decision = str(data.get("decision") or "").strip()

    lines = []

    # ------------------------------------------------------------
    # VERIFIED IDENTITY
    # ------------------------------------------------------------
    if tag:
        identity = f"{tag}"
        if description:
            identity += f" is {description}"
        if area:
            identity += f" in {area}"
        identity += "."

        lines.append(identity)

        details = []
        if io_type:
            details.append(f"I/O: {io_type}")
        if plc:
            details.append(f"PLC address: {plc}")
        if panel:
            details.append(f"Panel: {panel}")
        if tb:
            details.append(f"TB: {tb}")
        if terminals:
            details.append(f"Terminals: {terminals}")

        if details:
            lines.append("Verified field information: " + "; ".join(details) + ".")

    # ------------------------------------------------------------
    # EVIDENCE BOUNDARY
    # ------------------------------------------------------------
    no_verified_data = (
        "NO VERIFIED DATA" in evidence_status.upper()
        or "NO DATA" in evidence_status.upper()
        or "no verified maintenance evidence" in message.lower()
        or "no sufficiently strong verified maintenance history" in message.lower()
    )

    if no_verified_data:
        lines.append(
            "I don't have verified maintenance history identifying a specific "
            "failure cause for this problem, so I won't guess."
        )

        lines.append(
            "For a field investigation, check the signal chain systematically: "
            "instrument condition and power, the 4–20 mA loop, field wiring, "
            "termination connections, the corresponding PLC input, and the "
            "PLC/SCADA indication."
        )

        if tb or terminals or panel or plc:
            path = []

            if tb:
                tb_text = f"TB {tb}"
                if terminals:
                    tb_text += f" terminals {terminals}"
                path.append(tb_text)

            if panel:
                path.append(f"panel {panel}")

            if plc:
                path.append(f"PLC input {plc}")

            if path:
                lines.append(
                    "For this instrument, the verified signal path includes "
                    + ", ".join(path)
                    + ". Compare the field signal with the PLC/SCADA value "
                      "before concluding that the transmitter itself has failed."
                )

    else:
        if message:
            lines.append(message)

    # ------------------------------------------------------------
    # V5 DECISION / EVIDENCE
    # ------------------------------------------------------------
    if decision:
        lines.append(f"V5 decision: {decision}.")

    if evidence_status and not no_verified_data:
        lines.append(f"Evidence status: {evidence_status}.")

    # ------------------------------------------------------------
    # VERIFIED PLANT MEMORY
    # ------------------------------------------------------------
    if plant_memory_records:
        lines.append(
            f"ANVI found {plant_memory_count} verified Plant Memory "
            f"record(s) relevant to this equipment."
        )

        for memory in plant_memory_records[:5]:
            memory_id = str(
                memory.get("memory_id") or ""
            ).strip()

            event = str(
                memory.get("event") or ""
            ).strip()

            finding = str(
                memory.get("finding") or ""
            ).strip()

            action = str(
                memory.get("maintenance_action") or ""
            ).strip()

            outcome = str(
                memory.get("outcome") or ""
            ).strip()

            evidence = str(
                memory.get("confirmation_evidence") or ""
            ).strip()

            if memory_id:
                lines.append(f"Memory: {memory_id}.")

            if event:
                lines.append(f"Previous event: {event}.")

            if finding:
                lines.append(f"Finding: {finding}.")

            if action:
                lines.append(f"Previous action: {action}.")

            if outcome:
                lines.append(f"Outcome: {outcome}.")

            if evidence:
                lines.append(f"Confirmation evidence: {evidence}.")

        lines.append(
            "These are verified previous human field experiences, "
            "not automatic maintenance commands."
        )

    # ------------------------------------------------------------
    # SAFETY BOUNDARY
    # ------------------------------------------------------------
    lines.append(
        "This is read-only maintenance guidance. Human verification, "
        "permit requirements, isolation and risk assessment remain mandatory "
        "before field intervention."
    )

    return {
        "answer": " ".join(lines),
        "domain": "troubleshooting",
        "evidence": "verified PCI database + existing V5 maintenance intelligence",
        "equipment": tag or data.get("equipment"),

        # --------------------------------------------------------
        # EXPOSE VERIFIED PLANT MEMORY TO THE API CALLER
        # --------------------------------------------------------
        # The formatter may discover Plant Memory directly above.
        # Return the actual merged records/count so API/dashboard/
        # regression tests can consume them without parsing text.
        # --------------------------------------------------------
        "plant_memory_records": plant_memory_records,
        "plant_memory_count": len(plant_memory_records),

        "read_only": True,
        "human_decision_required": True,
        "plc_write": False,
        "scada_control": False,
        "v5_result": data,
    }



def _anvi_troubleshooting_memory_bridge(question, tag="", pci_record=None):
    """
    Resolve Plant Memory relevant to a troubleshooting question.

    This is an evidence bridge only. It does not perform diagnosis,
    maintenance execution, PLC writes or SCADA control.

    Memory verification state is preserved:
      VERIFIED            -> verified historical evidence
      PENDING_VERIFICATION -> reported historical clue
    """
    try:
        resolved_tag = str(tag or "").strip()

        if not resolved_tag:
            try:
                resolved_tag, resolved_record = _tag_from_question(question)
                if pci_record is None and isinstance(resolved_record, dict):
                    pci_record = resolved_record
            except Exception:
                resolved_tag = ""

        if not resolved_tag:
            return []

        records = _anvi_search_memory_for_tag(
            tag=resolved_tag,
            limit=20
        )

        return [
            r for r in records
            if isinstance(r, dict)
            and (
                str(r.get("tag") or "").strip().lower()
                in {
                    str(v).strip().lower()
                    for v in _anvi_memory_tag_variants(resolved_tag)
                }
            )
        ]

    except Exception:
        return []


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
        "abnormal pressure",
        "abnormal indication",
        "abnormal signal",
        "pressure abnormal",
        "pressure indication abnormal",
        "signal abnormal",
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




def _anvi_establish_explicit_pci_context(question):
    """
    Establish conversational PCI context from an explicit REAL PCI tag.

    IMPORTANT:
    - Uses the authoritative PCI registry.
    - Matches complete database tags, including tags containing multiple
      underscores such as LP_1_Healthy and MCV_204_control_On.
    - Never falls back to remembered context.
    - Never invents or modifies a tag.
    """
    try:
        from pci_registry import search

        q = str(question or "").strip()
        if not q:
            return None

        q_upper = q.upper()

        # ------------------------------------------------------------
        # 1. EXACT COMPLETE TAG MATCH AGAINST THE REAL PCI REGISTRY
        # ------------------------------------------------------------
        records = search(query=None, limit=1064)

        # Longest tags first prevents a shorter tag from winning when
        # one tag is contained inside another.
        records = sorted(
            records,
            key=lambda r: len(str(r.get("tag", ""))),
            reverse=True,
        )

        for record in records:
            tag = str(record.get("tag", "")).strip()
            if not tag:
                continue

            tag_upper = tag.upper()

            # Exact token boundary around the complete database tag.
            pattern = r"(?<![A-Z0-9_])" + re.escape(tag_upper) + r"(?![A-Z0-9_])"

            if re.search(pattern, q_upper):
                _remember_pci_context(record=record)
                return record

        # ------------------------------------------------------------
        # 2. NORMALIZED PREFIX+NUMBER TAGS
        # ------------------------------------------------------------
        # Examples:
        # PT303 / PT 303 / PT-303 -> PT_303
        normalized = _normalize_pci_instrument_tags(q)

        if normalized != q:
            normalized_upper = normalized.upper()

            for record in records:
                tag = str(record.get("tag", "")).strip()
                if not tag:
                    continue

                tag_upper = tag.upper()
                pattern = (
                    r"(?<![A-Z0-9_])"
                    + re.escape(tag_upper)
                    + r"(?![A-Z0-9_])"
                )

                if re.search(pattern, normalized_upper):
                    _remember_pci_context(record=record)
                    return record

    except Exception:
        pass

    return None


def _anvi_direct_pci_followup(question):
    """
    Resolve simple conversational follow-ups against the last
    verified PCI instrument.

    This is deterministic evidence retrieval, not a second
    reasoning engine.
    """
    record = _ANVI_CONVERSATION_CONTEXT.get("last_pci_record")

    if not isinstance(record, dict):
        return None

    ql = str(question or "").lower().strip()

    tag = (
        record.get("tag")
        or record.get("instrument_tag")
        or record.get("name")
        or ""
    )

    if not tag:
        return None

    description = (
        record.get("description")
        or record.get("instrument")
        or record.get("title")
        or ""
    )

    area = (
        record.get("area")
        or record.get("location")
        or ""
    )

    plc = (
        record.get("plc_address")
        or record.get("plc")
        or record.get("address")
        or ""
    )

    panel = record.get("panel") or ""

    tb = (
        record.get("tb")
        or record.get("terminal_block")
        or ""
    )

    terminals = (
        record.get("terminal")
        or record.get("terminals")
        or record.get("terminal_reference")
        or ""
    )

    # PLC address
    if any(x in ql for x in [
        "what is the plc address",
        "what's the plc address",
        "plc address",
        "which plc address",
        "plc tag",
    ]):
        if plc:
            return {
                "answer": f"The PLC address for {tag} is {plc}.",
                "domain": "pci",
                "context_tag": tag,
                "conversation_context": True,
                "read_only": True,
            }

    # Location / area
    if any(x in ql for x in [
        "where is it",
        "where is this",
        "which area is it",
        "what area is it",
        "which area",
        "what area",
    ]):
        if area:
            return {
                "answer": (
                    f"{tag} is in {area}."
                    + (
                        f" It is described as {description}."
                        if description else ""
                    )
                ),
                "domain": "pci",
                "context_tag": tag,
                "conversation_context": True,
                "read_only": True,
            }

    # Panel
    if any(x in ql for x in [
        "which panel",
        "what panel",
        "panel is it connected to",
        "which panel is it connected to",
    ]):
        if panel:
            return {
                "answer": f"{tag} is mapped to panel {panel}.",
                "domain": "pci",
                "context_tag": tag,
                "conversation_context": True,
                "read_only": True,
            }

    # What does it measure?
    if any(x in ql for x in [
        "what does it measure",
        "what is it measuring",
        "what does this measure",
        "what is this measuring",
    ]):
        if description:
            return {
                "answer": (
                    f"The verified PCI description for {tag} is "
                    f"'{description}'."
                ),
                "domain": "pci",
                "context_tag": tag,
                "conversation_context": True,
                "read_only": True,
            }

    # TB / terminal block
    if any(x in ql for x in [
        "which tb",
        "what tb",
        "terminal block",
        "which terminal",
        "what terminal",
        "termination",
    ]):
        if tb or terminals:
            answer = f"{tag} is associated with"
            if tb:
                answer += f" TB {tb}"
            if terminals:
                answer += f" and terminal reference {terminals}"
            answer += "."

            return {
                "answer": answer,
                "domain": "pci",
                "context_tag": tag,
                "conversation_context": True,
                "read_only": True,
            }

    return None



def _normalize_pci_instrument_tags(question):
    """
    Normalize natural-language instrument tag variants before PCI routing.

    Examples:
      PT_303 -> PT_303
      PT-303 -> PT_303
      PT 303 -> PT_303
      PT303  -> PT_303
      CV-101 -> CV_101
      CV 101 -> CV_101

    Only known industrial instrument/equipment prefixes are normalized.
    No database values are invented or changed.
    """
    text = str(question or "")

    prefixes = (
        "PT", "FT", "TT", "LT", "AT", "CV", "FV", "XV",
        "PV", "TV", "LV", "PCV", "FCV", "TCV", "LCV",
        "PIC", "FIC", "TIC", "LIC", "P", "M", "AI", "AO",
        "DI", "DO"
    )

    prefix_pattern = "|".join(sorted(prefixes, key=len, reverse=True))

    pattern = re.compile(
        rf"(?<![A-Za-z0-9])({prefix_pattern})[\s_-]*(\d{{1,6}})(?![A-Za-z0-9])",
        re.IGNORECASE,
    )

    def repl(match):
        return f"{match.group(1).upper()}_{match.group(2)}"

    return pattern.sub(repl, text)



# ============================================================
# ANVIQO V1.2 ROUTING PRIORITY FIX
# ============================================================

def _is_troubleshooting_question(q):
    """
    Detect explicit troubleshooting/diagnostic requests.

    This MUST take priority over generic PCI information lookup.
    It does not create a new reasoning engine.
    """
    ql = str(q or "").strip().lower()

    phrases = [
        "what should i check",
        "what should we check",
        "what do i check",
        "what do we check",
        "what can i check",
        "what can we check",
        "how do i troubleshoot",
        "how should i troubleshoot",
        "how can i troubleshoot",
        "troubleshoot this",
        "troubleshoot it",
        "troubleshooting",
        "what could be wrong",
        "what might be wrong",
        "what is wrong",
        "why is it faulty",
        "why is it failing",
        "why did it fail",
        "possible cause",
        "possible causes",
        "diagnose this",
        "diagnose it",
        "diagnostic check",
        "checks to perform",
        "checks should i perform",
    ]

    return any(p in ql for p in phrases)


def _memory_response_contract(result):
    """
    Normalize Plant Memory responses without changing their meaning.
    """
    if not isinstance(result, dict):
        return result

    if result.get("domain") in {
        "plant_memory",
        "verified_action_recall",
        "pci_plant_memory",
    }:
        result.setdefault("read_only", True)
        result.setdefault("plc_write", False)
        result.setdefault("scada_control", False)

        if result.get("verification") == "VERIFIED":
            result.setdefault("human_decision_required", True)

        if "memory_id" not in result:
            reports = result.get("reports") or []
            if reports:
                result["memory_id"] = reports[0].get("memory_id")

        if result.get("domain") == "plant_memory":
            result.setdefault(
                "human_decision_required",
                True
            )

    return result

def ask_anvi(question):
    # Normalize natural-language PCI/instrument tag variants before
    # any routing, context lookup, PCI lookup, troubleshooting or LLM fallback.
    question = _normalize_pci_instrument_tags(question)
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
        # CONVERSATIONAL PLANT MEMORY WRITE
        # ============================================================
        # Explicit "remember/save/store maintenance history" commands
        # create a PENDING_VERIFICATION memory record.
        #
        # This must happen before normal question routing.
        # ============================================================
        if _is_memory_write_command(q):
            memory_write_result = _plant_memory_write_route(q)

            if isinstance(memory_write_result, dict):
                return memory_write_result

        # ============================================================
        # PLANT MEMORY — BEFORE VERIFIED PCI TAG ROUTING
        # ============================================================
        # A question may contain a valid PCI tag AND still be a
        # Plant Memory question.
        #
        # Example:
        #   Have we seen PT-303 abnormal pressure before?
        #   What action fixed PT-303 previously?
        #
        # These MUST reach Plant Memory before the PCI identity route.
        # ============================================================

        if _is_memory_question(q):
            try:
                memory_result = _pci_memory_route(q)

                if isinstance(memory_result, dict):
                    return memory_result

            except Exception:
                pass

        # ============================================================
        # SPARE / INVENTORY INTENT PRIORITY
        # ============================================================
        # ============================================================
        # SPARE / INVENTORY INTENT PRIORITY
        # ============================================================
        # Explicit spare/inventory questions must reach the
        # deterministic spare engine BEFORE verified PCI-tag
        # identity routing.
        #
        # Example:
        #   Do we have a spare for PT303?
        # -> PT-303 | qty=0 | indent=1
        #
        # Ordinary engineering questions such as:
        #   Tell me about PT303
        # continue through the PCI identity route below.
        # ============================================================

        spare_intent_terms = (
            "spare",
            "spares",
            "critical spare",
            "critical spares",
            "inventory",
            "in stock",
            "stock available",
            "available as a spare",
            "available spare",
            "available spares",
            "to indent",
            "indent",
        )

        if any(term in ql for term in spare_intent_terms):
            try:
                import pci_conversation as pc

                spare_result = pc.answer(q)

                if isinstance(spare_result, dict):
                    spare_domain = str(
                        spare_result.get("domain", "")
                    ).lower()

                    spare_records = spare_result.get("records")

                    if (
                        spare_domain == "critical_spares"
                        or (
                            isinstance(spare_records, list)
                            and len(spare_records) > 0
                            and any(
                                "spare" in str(
                                    spare_result.get("answer", "")
                                ).lower()
                                for _ in [0]
                            )
                        )
                    ):
                        return spare_result

            except Exception:
                pass

        # ============================================================
        # VERIFIED PCI TAG — RESOLVE CONTEXT, DO NOT RETURN YET
        # ============================================================
        # A verified PCI tag may also be part of a troubleshooting
        # question. Resolve the record first, but allow the authoritative
        # troubleshooting route below to take priority.
        #
        # Example:
        #   What should I check for PT-303?
        #
        # MUST reach V5 maintenance intelligence rather than returning
        # only the PCI identity record.
        # ============================================================
        pci_tag = None
        pci_item = None

        try:
            pci_tag, pci_item = _tag_from_question(q)
        except Exception:
            pci_tag, pci_item = None, None

        if pci_tag and pci_item:
            try:
                _remember_pci_context(record=pci_item)
            except Exception:
                pass

            # --------------------------------------------------------
            # TROUBLESHOOTING OVERRIDES NORMAL PCI IDENTITY ANSWER
            # --------------------------------------------------------
            if _anvi_troubleshooting_question(q):
                tag = str(
                    pci_item.get("tag")
                    or pci_item.get("instrument_tag")
                    or pci_item.get("name")
                    or pci_tag
                    or ""
                ).strip()

                try:
                    maintenance_result = _maintenance(
                        f"{q} [{tag}]"
                    )
                except Exception:
                    maintenance_result = _maintenance(q)

                formatted = _anvi_conversational_maintenance_answer(
                    q,
                    maintenance_result,
                    pci_record=pci_item,
                )

                if isinstance(formatted, dict):
                    return formatted

                return {
                    "answer": str(formatted),
                    "domain": "troubleshooting",
                    "equipment": tag,
                    "context_tag": tag,
                    "read_only": True,
                    "human_decision_required": True,
                    "plc_write": False,
                    "scada_control": False,
                }

            # Normal PCI question — return the verified identity record.
            return {
                "answer": (
                    f"{pci_tag}: {pci_item.get('description','No description available')}. "
                    f"Area: {pci_item.get('area','UNKNOWN')}. "
                    f"I/O type: {pci_item.get('io_type','UNKNOWN')}. "
                    f"PLC address: {pci_item.get('plc_address','UNKNOWN')}. "
                    f"Panel: {pci_item.get('panel','UNKNOWN')}. "
                    f"TB: {pci_item.get('tb_name','UNKNOWN')} "
                    f"{pci_item.get('tb_no','')}. "
                    f"Source: {pci_item.get('source_sheet','UNKNOWN')}."
                ),
                "domain": "pci",
                "tag": pci_tag,
                "evidence": "verified PCI database",
                "record": pci_item,
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
            }

        # ============================================================
        # 0. PCI SEMANTIC COLLECTION QUERY — BEFORE EXACT TAG CONTEXT
        # ============================================================
        # IMPORTANT:
        # Questions such as:
        #   Which instruments are DI?
        #   Which instruments are in VRM / MILL?
        #   Show me instruments on panel C2
        # must be handled by the deterministic PCI registry before
        # exact-tag context. Otherwise a database tag such as "DI"
        # can hijack the question.

        if _is_pci_question(q):
            try:
                import pci_conversation as pc
                semantic_result = pc.answer(q)

                if isinstance(semantic_result, dict):
                    if semantic_result.get("records") or (
                        semantic_result.get("count") is not None
                        and semantic_result.get("evidence") == "verified PCI database"
                    ):
                        records = semantic_result.get("records")
                        if isinstance(records, list):
                            _remember_pci_context(results=records)

                        return semantic_result
            except Exception:
                pass

        # ============================================================
        # 1. EXPLICIT PCI TAG -> ESTABLISH CONTEXT FIRST
        # ============================================================
        #
        # This MUST happen before direct follow-up routing.
        # Example:
        #   Tell me about PT_303
        # establishes PT_303 as the active PCI context.
        #
        explicit_pci_record = _anvi_establish_explicit_pci_context(q)

        # ============================================================
        # FORCE VERIFIED PCI TROUBLESHOOTING PATH
        # ============================================================
        # If the user is troubleshooting the currently identified
        # instrument, resolve it directly through existing V5
        # maintenance intelligence and the conversational formatter.
        #
        # This MUST return here so older maintenance fallback routes
        # cannot intercept the question.

        if _anvi_troubleshooting_question(q):

            pci_context = (
                explicit_pci_record
                if isinstance(explicit_pci_record, dict)
                else _ANVI_CONVERSATION_CONTEXT.get("last_pci_record")
            )

            if isinstance(pci_context, dict):

                tag = str(
                    pci_context.get("tag")
                    or pci_context.get("instrument_tag")
                    or pci_context.get("name")
                    or ""
                ).strip()

                if tag:

                    try:
                        maintenance_result = _maintenance(
                            f"{q} [{tag}]"
                        )
                    except Exception:
                        maintenance_result = _maintenance(q)

                    formatted = _anvi_conversational_maintenance_answer(
                        q,
                        maintenance_result,
                        pci_record=pci_context,
                    )

                    if isinstance(formatted, dict):
                        return formatted

                    return {
                        "answer": str(formatted),
                        "domain": "troubleshooting",
                        "equipment": tag,
                        "context_tag": tag,
                        "read_only": True,
                        "human_decision_required": True,
                        "plc_write": False,
                        "scada_control": False,
                    }


        # ============================================================
        # TROUBLESHOOTING PRIORITY — BEFORE PCI ANSWER ROUTING
        # ============================================================
        # PCI context is established first, but troubleshooting questions
        # MUST go to the existing V5/Maintenance intelligence layer.
        # This prevents the PCI semantic route from answering with only
        # the instrument record.

        troubleshooting_intent = _anvi_troubleshooting_question(q)

        if troubleshooting_intent:
            previous = _ANVI_CONVERSATION_CONTEXT.get("last_pci_record")

            if isinstance(previous, dict):
                tag = str(
                    previous.get("tag")
                    or previous.get("instrument_tag")
                    or previous.get("name")
                    or ""
                ).strip()

                if tag:
                    try:
                        answer = _maintenance(f"{q} [{tag}]")
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
        # DIRECT PCI FOLLOW-UP FROM VERIFIED CONVERSATION CONTEXT
        # ============================================================
        direct_pci = _anvi_direct_pci_followup(q)

        if direct_pci:
            return direct_pci

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
            "areas require attention",
            "which areas require attention",
            "areas need attention",
            "which areas need attention",
            "problem areas",
            "critical areas",
            "degraded areas",
            "areas at risk",
            "plant risk",
            "risks in the plant",
            "what problems could develop",
            "what problems may develop",
            "what could go wrong",
            "what may go wrong",
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
        # Single authoritative troubleshooting route.
        #
        # Flow:
        #   verified/current PCI context
        #       -> Plant Memory historical evidence
        #       -> existing V5 maintenance intelligence
        #       -> conversational technician response
        #
        # Plant Memory is evidence only. It never becomes an automatic
        # maintenance command and never enables PLC/SCADA control.

        troubleshooting = _anvi_troubleshooting_question(q)

        if troubleshooting:

            previous = _ANVI_CONVERSATION_CONTEXT.get(
                "last_pci_record"
            )

            tag = ""

            if isinstance(previous, dict):
                tag = str(
                    previous.get("tag")
                    or previous.get("instrument_tag")
                    or previous.get("name")
                    or ""
                ).strip()

            # If the question itself contains an explicit PCI tag, resolve it
            # instead of depending on prior conversational context.
            if not tag:
                try:
                    resolved_tag, resolved_record = _tag_from_question(q)

                    if resolved_tag:
                        tag = str(resolved_tag).strip()

                        if not isinstance(previous, dict):
                            previous = resolved_record

                except Exception:
                    pass

            memory_records = _anvi_troubleshooting_memory_bridge(
                q,
                tag=tag,
                pci_record=previous,
            )

            historical_context = ""

            if memory_records:
                historical_context = (
                    "\n\nHistorical Plant Memory context "
                    "(evidence status must be preserved):\n"
                )

                for memory in memory_records:
                    status = str(
                        memory.get("verification_status")
                        or (
                            "VERIFIED"
                            if memory.get("verified") is True
                            else "PENDING_VERIFICATION"
                        )
                    ).strip()

                    historical_context += (
                        f"- Memory ID: {memory.get('memory_id', '')}; "
                        f"Tag: {memory.get('tag', '')}; "
                        f"Status: {status}; "
                        f"Previous event: {memory.get('event', '')}; "
                        f"Observation: {memory.get('observation', '')}; "
                        f"Finding: {memory.get('finding', '')}; "
                        f"Previous action: {memory.get('maintenance_action', '')}; "
                        f"Outcome: {memory.get('outcome', '')}; "
                        f"Recovery: {memory.get('recovery_status', '')}; "
                        f"Confirmation: {memory.get('confirmation_evidence', '')}; "
                        f"Spare used: {memory.get('spare_used', '')}.\n"
                    )

            maintenance_question = q

            if tag:
                maintenance_question += f" [{tag}]"

            if historical_context:
                maintenance_question += historical_context

            try:
                maintenance_result = _maintenance(
                    maintenance_question
                )
            except Exception:
                try:
                    maintenance_result = _maintenance(
                        f"{q} [{tag}]" if tag else q
                    )
                except Exception:
                    maintenance_result = {
                        "equipment": tag,
                        "evidence_status": "NO VERIFIED DATA",
                        "recommendation": {
                            "message": "No verified maintenance evidence was found."
                        },
                    }

            if isinstance(maintenance_result, dict):
                existing = maintenance_result.get(
                    "plant_memory_records"
                )

                if not isinstance(existing, list):
                    existing = []

                known = {
                    x.get("memory_id")
                    for x in existing
                    if isinstance(x, dict)
                }

                for memory in memory_records:
                    mid = memory.get("memory_id")

                    if mid and mid not in known:
                        existing.append(memory)
                        known.add(mid)

                maintenance_result["plant_memory_records"] = existing
                maintenance_result["plant_memory_count"] = len(existing)

            # Preserve Plant Memory records in the result consumed by
            # the existing conversational maintenance formatter.
            if not isinstance(maintenance_result, dict):
                maintenance_result = {}

            maintenance_result["plant_memory_records"] = list(memory_records)
            maintenance_result["plant_memory_count"] = len(memory_records)

            return _anvi_conversational_maintenance_answer(
                q,
                maintenance_result,
                pci_record=previous,
            )

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

