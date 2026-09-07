from pci_universal_resolver import resolve as _universal_pci_resolve
import re
"""
ANVIQO PCI CONVERSATION LAYER
=============================

Natural-language retrieval over the verified PCI registry.

This layer:
- Uses the existing 1,064 PCI records.
- Does not duplicate V5 reasoning.
- Does not invent plant data.
- Maintains lightweight conversation context.
- Supports follow-up questions such as:
    "Tell me about LP_1_Healthy"
    "Where is it?"
    "What is the PLC address?"
    "Which panel?"
    "Which TB?"
- Read-only.
"""

from pci_registry import (
    find_tag,
    search,
    search_area,
    search_pressure_transmitters,
    search_critical,
    compact,
)


from pci_live_simulator import get_live_pci_snapshot


def _live_point(tag):
    """
    Return the current DEMO SIMULATION point for an exact PCI tag.

    The simulator is read-only and uses the verified 1,064-record
    PCI database as its identity source.
    """
    snapshot = get_live_pci_snapshot()

    target = str(tag or "").strip().upper()

    for point in snapshot.get("points", []):
        if str(point.get("tag", "")).strip().upper() == target:
            return point

    return None


def _state_sentence(record):
    """
    Describe current simulated state without presenting it as
    real plant data.
    """
    if not record:
        return "No current PCI simulation state is available."

    tag = record.get("tag", "")
    state = record.get("state", "UNKNOWN")
    value = record.get("value", "")
    changed = record.get("changed", False)
    event = record.get("event_active", False)

    parts=[
        f"In the current PCI DEMO SIMULATION, {tag} is {state}."
    ]

    if value != "":
        parts.append(f"Simulated value: {value}.")

    if changed:
        parts.append("The simulator currently marks this point as changed.")

    if event:
        parts.append(
            "The simulator currently marks an associated event as active."
        )

    return " ".join(parts)


_CONTEXT = {
    "last_record": None,
    "last_results": [],
}


def _remember(record=None, results=None):
    if record is not None:
        _CONTEXT["last_record"] = record
    if results is not None:
        _CONTEXT["last_results"] = results


def _record_text(r):
    return (
        f"{r.get('tag','')} — "
        f"{r.get('description','')}; "
        f"Area: {r.get('area','UNKNOWN')}; "
        f"I/O: {r.get('io_type','UNKNOWN')}; "
        f"PLC address: {r.get('plc_address','UNKNOWN')}; "
        f"Panel: {r.get('panel','UNKNOWN')}; "
        f"TB: {r.get('tb_name','UNKNOWN')} "
        f"{r.get('tb_no','')}"
    )



def _natural_family_io_question(q):
    """
    Resolve natural-language equipment-family + I/O questions.

    Examples:
      what is the DO for MCV 204
      show me MCV 204 DO
      MCV-204 digital output
      tell me the DOs of MCV 204

    Uses ONLY authoritative PCI resolver results.
    No tag or I/O point is invented.
    """
    import re

    text = str(q or "").strip()

    m = re.search(
        r"\b(MCV|PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|FV|XV)"
        r"[\s_-]*(\d+)\b"
        r".{0,80}?"
        r"\b(DI|DO|AI|AO|DIGITAL\s+INPUT|DIGITAL\s+OUTPUT|"
        r"ANALOG\s+INPUT|ANALOG\s+OUTPUT)\b",
        text,
        flags=re.IGNORECASE,
    )

    reverse = re.search(
        r"\b(DI|DO|AI|AO|DIGITAL\s+INPUT|DIGITAL\s+OUTPUT|"
        r"ANALOG\s+INPUT|ANALOG\s+OUTPUT)\b"
        r".{0,80}?"
        r"\b(MCV|PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|FV|XV)"
        r"[\s_-]*(\d+)\b",
        text,
        flags=re.IGNORECASE,
    )

    if m:
        prefix = m.group(1).upper()
        number = m.group(2)
        io_raw = m.group(3).upper()
    elif reverse:
        io_raw = reverse.group(1).upper()
        prefix = reverse.group(2).upper()
        number = reverse.group(3)
    else:
        return None

    io_map = {
        "DI": "DI",
        "DO": "DO",
        "AI": "AI",
        "AO": "AO",
        "DIGITAL INPUT": "DI",
        "DIGITAL OUTPUT": "DO",
        "ANALOG INPUT": "AI",
        "ANALOG OUTPUT": "AO",
    }

    io_type = io_map.get(io_raw)
    if not io_type:
        return None

    family = f"{prefix}{number}"

    try:
        rows, mode = _universal_pci_resolve(
            f"{family} {io_type}"
        )
    except Exception:
        return None

    if not rows:
        return None

    # Only accept the resolver's explicit family-I/O result.
    if mode not in ("NATURAL_FAMILY_IO", "FAMILY_IO"):
        return None

    lines = [
        f"ANVI found {len(rows)} verified {io_type} point(s) for {prefix}-{number}:"
    ]

    for r in rows:
        tag = r.get("tag", "UNKNOWN")
        desc = r.get("description", "No description available")
        plc = r.get("plc_address", "UNKNOWN")
        panel = r.get("panel", "UNKNOWN")
        tb_name = r.get("tb_name", "UNKNOWN")
        tb_no = r.get("tb_no", "")
        source = r.get("source_sheet", "UNKNOWN")

        lines.append(
            f"- {desc} — {tag} — PLC {plc} — Panel {panel} — "
            f"TB {tb_name} {tb_no}"
        )

    lines.append(
        f"Source: {rows[0].get('source_sheet', 'UNKNOWN')}."
    )
    lines.append(
        "This is verified PCI evidence in read-only mode. "
        "No PLC or SCADA command is executed."
    )

    _remember(results=rows)

    return "\n".join(lines)


def _find_tag_in_question(q):
    """
    UNIVERSAL VERIFIED PCI TAG/FAMILY RESOLUTION.
    """
    rows, mode = _universal_pci_resolve(q)

    if not rows:
        return None

    return rows[0]

def _semantic_pci_query(question):
    """
    Deterministic semantic query parser for the verified PCI registry.

    IMPORTANT:
    This runs before exact-tag interpretation so words such as DI, AI,
    DO and AO cannot accidentally be interpreted as instrument tags.
    """

    q = str(question or "").strip()
    ql = q.lower()

    from pci_registry import (
        semantic_search_pci,
        search_pressure_transmitters,
        search_control_valves,
        search_critical,
        search_panel,
        search_tb,
    )

    def result(title, records):
        _remember(results=records)

        if not records:
            return {
                "answer": f"I found 0 verified PCI records for {title}.",
                "domain": "pci",
                "evidence": "verified PCI database",
                "count": 0,
                "records": [],
                "read_only": True,
            }

        preview = records[:20]

        return {
            "answer": (
                f"I found {len(records)} verified PCI records for {title}. "
                f"I am showing the first {len(preview)} records."
            ),
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(records),
            "records": [compact(r) for r in preview],
            "read_only": True,
        }

    # --------------------------------------------------------
    # Panel queries
    # --------------------------------------------------------
    m = re.search(r"\bpanel\s*([A-Za-z0-9_-]+)\b", q, re.I)
    if m and any(x in ql for x in (
        "connected", "connected to", "on panel", "in panel",
        "panel", "instruments"
    )):
        panel = m.group(1).upper()
        records = search_panel(panel, limit=1064)
        return result(f"panel {panel}", records)

    # --------------------------------------------------------
    # TB / terminal block queries
    # --------------------------------------------------------
    m = re.search(r"\b(?:tb|terminal block)\s*([A-Za-z]{1,5}\s*[-_]?\s*\d+)\b", q, re.I)
    if m and any(x in ql for x in ("tag", "tags", "connected", "use", "using", "instruments", "tb")):
        tb = re.sub(r"[\s_-]+", "", m.group(1)).upper()
        records = search_tb(tb, limit=1064)
        return result(f"TB {tb}", records)

    # --------------------------------------------------------
    # I/O type queries
    # --------------------------------------------------------
    io_match = re.search(
        r"\b(?:which instruments are|show me instruments that are|show me)\s+"
        r"(AI\s*\(?(?:4-20mA|RTD)\)?|AI|AO|DI|DO)\b",
        q,
        re.I,
    )

    if io_match:
        io_raw = io_match.group(1).upper().replace(" ", "")
        if io_raw in ("AI4-20MA", "AI(4-20MA)"):
            io_type = "AI (4-20mA)"
        elif io_raw in ("AIRT D", "AI(RTD)"):
            io_type = "AI (RTD)"
        else:
            io_type = io_raw

        records = semantic_search_pci(io_type=io_type, limit=1064)
        return result(f"I/O type {io_type}", records)

    # More permissive exact I/O questions.
    for io_type in ("AI (4-20mA)", "AI (RTD)", "DI", "DO", "AO"):
        token = io_type.lower().replace(" ", "")
        if (
            f"which instruments are {token}" in ql.replace(" ", "")
            or f"instruments are {io_type.lower()}" in ql
            or f"instruments that are {io_type.lower()}" in ql
        ):
            records = semantic_search_pci(io_type=io_type, limit=1064)
            return result(f"I/O type {io_type}", records)

    # --------------------------------------------------------
    # VERIFIED TRANSMITTER CLASS QUERIES
    #
    # Resolve natural-language instrument classes against the
    # existing PCI registry. Never invent an instrument identity.
    #
    # Examples:
    #   all flow transmitters
    #   show me all flow transmitters
    #   what are the flow transmitters
    #   all pressure transmitters
    #   all temperature transmitters
    #   all level transmitters
    # --------------------------------------------------------
    transmitter_classes = {
        "flow": [
            "flow transmitter",
            "flow transmitters",
            "flow measurement",
            "flow meter",
            "flow meters",
        ],
        "pressure": [
            "pressure transmitter",
            "pressure transmitters",
        ],
        "temperature": [
            "temperature transmitter",
            "temperature transmitters",
        ],
        "level": [
            "level transmitter",
            "level transmitters",
        ],
    }

    requested_class = None
    for cls, phrases in transmitter_classes.items():
        if any(phrase in ql for phrase in phrases):
            requested_class = cls
            break

    if requested_class == "flow":
        records = semantic_search_pci(
            kind="flow",
            limit=1064,
        )

        # Some verified PCI descriptions identify flow instruments
        # by description rather than the literal phrase "flow transmitter".
        if not records:
            records = semantic_search_pci(
                kind="flow_meter",
                limit=1064,
            )

        return result("flow transmitters", records)

    # --------------------------------------------------------
    # Pressure transmitters
    # --------------------------------------------------------
    if requested_class == "pressure":
        area = None

        if "vrm / mill" in ql or "vrm/mill" in ql or "vrm mill" in ql:
            area = "VRM / MILL"

        records = semantic_search_pci(
            kind="pressure_transmitter",
            area=area,
            limit=1064,
        )

        title = "pressure transmitters"
        if area:
            title += f" in {area}"

        return result(title, records)

    # --------------------------------------------------------
    # Control valves / valves
    # --------------------------------------------------------
    if "control valve" in ql or "control valves" in ql:
        records = search_control_valves(limit=1064)
        return result("control valves", records)

    if (
        "which valves" in ql
        or "show me the valves" in ql
        or "show me valves" in ql
    ):
        records = semantic_search_pci(kind="valve", limit=1064)
        return result("valves", records)

    # --------------------------------------------------------
    # Area queries
    # --------------------------------------------------------
    area_names = [
        "VRM / MILL",
        "PNEUMATIC / VALVES",
        "WEIGH FEEDING",
        "GAS / PROCESS",
        "BAG FILTER",
        "IGNITION",
        "PCI / GENERAL",
    ]

    for area in area_names:
        normalized = area.lower()
        if (
            normalized in ql
            and (
                "which instruments" in ql
                or "show me instruments" in ql
                or "instruments in" in ql
                or "what instruments" in ql
            )
        ):
            records = semantic_search_pci(area=area, limit=1064)
            return result(f"area {area}", records)

    # "in PCI" means the PCI/general registry area when no more specific
    # area is named.
    if (
        ("instruments in pci" in ql or "instrument in pci" in ql)
        and "critical" not in ql
    ):
        records = semantic_search_pci(area="PCI / GENERAL", limit=1064)
        return result("PCI / GENERAL", records)

    # --------------------------------------------------------
    # Criticality
    # --------------------------------------------------------
    if "critical" in ql and any(
        x in ql for x in ("instrument", "instruments", "i/o", "io", "tags")
    ):
        records = search_critical(limit=1064)
        return result("HIGH criticality", records)

    # --------------------------------------------------------
    # TB query with compact forms such as XC101
    # --------------------------------------------------------
    m = re.search(r"\b(X[A-Z]{1,3}\d{2,4})\b", q.upper())
    if m and any(x in ql for x in ("tb", "terminal", "tags use", "connected")):
        tb = m.group(1)
        records = search_tb(tb, limit=1064)
        return result(f"TB {tb}", records)

    return None



def _semantic_filter_query(q):
    """
    Convert natural-language PCI questions into deterministic
    structured searches against the verified PCI registry.

    This is NOT a reasoning engine.
    It only identifies explicit search constraints.
    """
    import re
    import pci_registry as registry

    ql = str(q or "").lower().strip()

    # ------------------------------------------------------------
    # AREA
    # ------------------------------------------------------------
    area = None
    area_patterns = [
        ("VRM / MILL", ["vrm / mill", "vrm/mill", "vrm mill"]),
        ("PNEUMATIC / VALVES", ["pneumatic / valves", "pneumatic/valves",
                                "pneumatic valves"]),
        ("WEIGH FEEDING", ["weigh feeding", "weigh-feeding"]),
        ("GAS / PROCESS", ["gas / process", "gas/process", "gas process"]),
        ("BAG FILTER", ["bag filter"]),
        ("IGNITION", ["ignition"]),
        ("PCI / GENERAL", ["pci / general", "pci/general", "pci general"]),
    ]

    for canonical, patterns in area_patterns:
        if any(x in ql for x in patterns):
            area = canonical
            break

    # ------------------------------------------------------------
    # PANEL
    # ------------------------------------------------------------
    panel = None
    m = re.search(r"\bpanel\s*[-_:]?\s*([A-Za-z]\d+)\b", q, re.I)
    if m:
        panel = m.group(1).upper()

    # ------------------------------------------------------------
    # TB / TERMINAL BLOCK
    # ------------------------------------------------------------
    tb_name = None
    m = re.search(
        r"\b(?:tb|terminal\s*block|terminal)\s*[-_:]?\s*([A-Za-z]{2,4}\d{2,4})\b",
        q,
        re.I,
    )
    if m:
        tb_name = m.group(1).upper()

    # ------------------------------------------------------------
    # I/O TYPE
    # ------------------------------------------------------------
    io_type = None

    if re.search(r"\bai\s*\(\s*4\s*-\s*20\s*m?a\s*\)", q, re.I):
        io_type = "AI (4-20mA)"
    elif re.search(r"\bai\s*4\s*-\s*20\s*m?a\b", q, re.I):
        io_type = "AI (4-20mA)"
    elif re.search(r"\banalog\s+input\b", ql):
        io_type = "AI (4-20mA)"
    elif re.search(r"\bai\b", ql):
        io_type = "AI"
    elif re.search(r"\bdi\b", ql):
        io_type = "DI"
    elif re.search(r"\bdo\b", ql):
        io_type = "DO"
    elif re.search(r"\bao\b", ql):
        io_type = "AO"

    # Exact AI means both AI types.
    io_broad = bool(io_type == "AI")

    # ------------------------------------------------------------
    # EQUIPMENT / INSTRUMENT CLASS
    # ------------------------------------------------------------
    description = None

    if "pressure transmitter" in ql or "pressure transmitters" in ql:
        description = "pressure transmitter"
    elif (
        "control valve" in ql
        or "control valves" in ql
        or "control-valve" in ql
    ):
        description = "control valve"
    elif "temperature transmitter" in ql:
        description = "temperature transmitter"
    elif "level transmitter" in ql:
        description = "level transmitter"
    elif "flow transmitter" in ql:
        description = "flow transmitter"
    elif "flow meter" in ql or "flow meters" in ql:
        description = "flow"
    elif "valve" in ql and not "panel" in ql:
        description = "valve"

    # ------------------------------------------------------------
    # CRITICALITY
    # ------------------------------------------------------------
    criticality = None
    if "critical" in ql:
        criticality = "HIGH"

    # ------------------------------------------------------------
    # Return structured intent
    # ------------------------------------------------------------
    return {
        "area": area,
        "panel": panel,
        "tb_name": tb_name,
        "io_type": io_type,
        "io_broad": io_broad,
        "description": description,
        "criticality": criticality,
    }


def _semantic_records(q):
    """
    Execute the structured semantic search.

    Important:
    - Uses only verified PCI registry records.
    - Does not invent tags.
    - Does not modify source records.
    """
    import pci_registry as registry

    intent = _semantic_filter_query(q)

    area = intent["area"]
    panel = intent["panel"]
    tb_name = intent["tb_name"]
    io_type = intent["io_type"]
    description = intent["description"]
    criticality = intent["criticality"]

    # Broad AI means AI (4-20mA) + AI (RTD)
    if io_type == "AI":
        records = [
            r for r in registry.load_records()
            if str(r.get("io_type", "")).upper().startswith("AI")
        ]

        if area:
            records = [
                r for r in records
                if str(r.get("area", "")).strip().lower() == area.lower()
            ]

        if panel:
            records = [
                r for r in records
                if str(r.get("panel", "")).strip().lower() == panel.lower()
            ]

        if tb_name:
            records = [
                r for r in records
                if str(r.get("tb_name", "")).strip().lower() == tb_name.lower()
            ]

        if description:
            records = [
                r for r in records
                if description.lower()
                in str(r.get("description", "")).lower()
            ]

        if criticality:
            records = [
                r for r in records
                if str(r.get("criticality", "")).upper() == criticality
            ]

        return records, intent

    # Standard structured registry search.
    records = registry.search(
        area=area,
        io_type=io_type if io_type in {
            "DI", "DO", "AO", "AI (4-20mA)", "AI (RTD)"
        } else None,
        description=description,
        panel=panel,
        tb_name=tb_name,
        criticality=criticality,
        limit=1064,
    )

    return records, intent


def _semantic_answer(question):
    """
    High-value deterministic semantic PCI answer.

    Returns None when the question is not a structured PCI search.
    """
    import pci_registry as registry

    q = str(question or "").strip()
    ql = q.lower()

    intent = _semantic_filter_query(q)

    has_structured_intent = any([
        intent["area"],
        intent["panel"],
        intent["tb_name"],
        intent["io_type"],
        intent["description"],
        intent["criticality"],
    ])

    # Don't intercept ordinary tag questions here.
    if not has_structured_intent:
        return None

    records, intent = _semantic_records(q)

    # Require actual matching constraints.
    if not records:
        filters = []

        if intent["description"]:
            filters.append(intent["description"])
        if intent["io_type"]:
            filters.append(intent["io_type"])
        if intent["area"]:
            filters.append(intent["area"])
        if intent["panel"]:
            filters.append(f"Panel {intent['panel']}")
        if intent["tb_name"]:
            filters.append(f"TB {intent['tb_name']}")
        if intent["criticality"]:
            filters.append("HIGH criticality")

        target = ", ".join(filters) if filters else q

        return {
            "answer": (
                f"I found 0 verified PCI records matching {target}. "
                "I won't invent an instrument identity."
            ),
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": 0,
            "records": [],
            "read_only": True,
        }

    compact = [registry.compact(r) for r in records]

    # ------------------------------------------------------------
    # HUMAN-FRIENDLY CATEGORY LABEL
    # ------------------------------------------------------------
    if intent["description"]:
        label = intent["description"]
    elif intent["io_type"]:
        label = intent["io_type"]
    elif intent["panel"]:
        label = f"Panel {intent['panel']}"
    elif intent["tb_name"]:
        label = f"TB {intent['tb_name']}"
    elif intent["area"]:
        label = intent["area"]
    elif intent["criticality"]:
        label = "HIGH-criticality instruments"
    else:
        label = "PCI records"

    # ------------------------------------------------------------
    # SUMMARY + RECORDS
    # ------------------------------------------------------------
    preview_limit = 20
    preview = compact[:preview_limit]

    if len(records) <= preview_limit:
        answer = (
            f"I found {len(records)} verified PCI records matching {label}. "
            "I can show their tags, descriptions, PLC addresses, panels and TBs."
        )
    else:
        answer = (
            f"I found {len(records)} verified PCI records matching {label}. "
            f"Showing the first {preview_limit}; the complete result set "
            "is available to the ANVIQO interface."
        )

    return {
        "answer": answer,
        "domain": "pci",
        "evidence": "verified PCI database",
        "count": len(records),
        "records": preview,
        "all_records": compact,
        "semantic_filters": intent,
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "human_decision_required": True,
    }


def answer(question):

    # --------------------------------------------------------
    # PRIORITY ROUTE: NATURAL EQUIPMENT FAMILY + I/O
    #
    # This MUST execute before generic exact/family resolution.
    # Example:
    #   "what is the DO for MCV 204"
    # must resolve to the verified MCV-204 DO family,
    # not the first MCV-204 signal such as MCV_204_Healthy.
    # --------------------------------------------------------
    natural_family_answer = _natural_family_io_question(question)
    if natural_family_answer:
        return {
            "answer": natural_family_answer,
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(_CONTEXT.get("last_results", [])),
            "records": [
                compact(r)
                for r in _CONTEXT.get("last_results", [])
            ],
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }

    """
    ANVI PCI conversational entry point.

    Priority:
    1. Explicit tag / exact record
    2. Structured semantic PCI search
    3. Existing PCI search behavior
    """
    import re
    import pci_registry as registry

    q = str(question or "").strip()
    ql = q.lower()

    if not q:
        return {
            "answer": "Please ask ANVI a PCI question.",
            "domain": "pci",
            "read_only": True,
        }

    # ------------------------------------------------------------
    # 1. EXACT TAG FIRST
    # ------------------------------------------------------------
    record = registry.find_tag(q)

    if record:
        return {
            "answer": (
                f"I found {record.get('tag')} in the verified PCI database. "
                f"It is {record.get('description') or 'not described'} "
                f"in {record.get('area') or 'an unspecified area'}. "
                f"It is {record.get('io_type') or 'an unspecified I/O type'} "
                f"with PLC address {record.get('plc_address') or 'not specified'}. "
                f"Panel: {record.get('panel') or 'not specified'}. "
                f"TB: {record.get('tb_name') or 'not specified'} "
                f"{record.get('tb_no') or ''}."
            ),
            "domain": "pci",
            "evidence": "verified PCI database",
            "record": registry.compact(record),
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }

    # ------------------------------------------------------------
    # 2. EXTRACT TAG FROM NATURAL LANGUAGE
    # ------------------------------------------------------------
    ids = re.findall(
        r"\b[A-Za-z]{1,16}[-_]?\d+(?:[-_][A-Za-z0-9]+)*\b",
        q.upper(),
    )

    for ident in ids:
        record = registry.find_tag(ident)
        if record:
            return {
                "answer": (
                    f"I found {record.get('tag')} in the verified PCI database. "
                    f"It is {record.get('description') or 'not described'} "
                    f"in {record.get('area') or 'an unspecified area'}. "
                    f"It is {record.get('io_type') or 'an unspecified I/O type'} "
                    f"with PLC address {record.get('plc_address') or 'not specified'}. "
                    f"Panel: {record.get('panel') or 'not specified'}. "
                    f"TB: {record.get('tb_name') or 'not specified'} "
                    f"{record.get('tb_no') or ''}."
                ),
                "domain": "pci",
                "evidence": "verified PCI database",
                "record": registry.compact(record),
                "read_only": True,
                "plc_write": False,
                "scada_control": False,
            }

    # ------------------------------------------------------------
    # 3. NEW STRUCTURED SEMANTIC SEARCH
    # ------------------------------------------------------------
    semantic = _semantic_answer(q)

    if semantic is not None:
        return semantic

    # ------------------------------------------------------------
    # 4. EXISTING GENERIC SEARCH FALLBACK
    # ------------------------------------------------------------
    results = registry.search(query=q, limit=100)

    if results:
        return {
            "answer": (
                f"I found {len(results)} matching PCI records in the "
                "verified database."
            ),
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(results),
            "records": [registry.compact(r) for r in results],
            "read_only": True,
        }

    return {
        "answer": (
            "I could not find a matching PCI record in the verified "
            "database. I won't invent an instrument identity."
        ),
        "domain": "pci",
        "evidence": "verified PCI database",
        "count": 0,
        "records": [],
        "read_only": True,
    }


# ============================================================
# ANVIQO PCI UNIVERSAL CONVERSATIONAL ANSWER FIX
# ============================================================
# Fixes:
# - PT-303 / PT303 / PT_303 exact lookup
# - TT-201 and other exact tags
# - "how many PCI I/O records"
# - "what instruments are in PCI"
# - "tell me about all I/O"
# - prevents stale previous-tag context from contaminating new questions
# - preserves verified PCI registry / read-only safety
# ============================================================

_PCI_ORIGINAL_ANSWER = answer

def _anviqo_norm_tag(value):
    import re
    if not value:
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())

def _anviqo_all_records():
    try:
        return search(query=None, limit=1064)
    except Exception:
        return []

def _anviqo_exact_record(question):
    import re

    q = str(question or "")
    uq = q.upper()

    # Detect conventional instrument tags:
    # PT-303, PT303, PT_303, TT-201, FT-101, LT-xxx, etc.
    candidates = re.findall(
        r"\b([A-Z]{1,6})[\s_-]?(\d{2,5})\b",
        uq
    )

    if not candidates:
        return None

    wanted = []
    for prefix, number in candidates:
        wanted.append(_anviqo_norm_tag(prefix + number))

    records = _anviqo_all_records()

    for r in records:
        fields = [
            r.get("tag"),
            r.get("fox_plc_tag"),
            r.get("instrument_tag"),
            r.get("name"),
        ]

        for field in fields:
            if _anviqo_norm_tag(field) in wanted:
                return r

    return None

def _anviqo_summary_answer(question):
    q = str(question or "").lower()
    records = _anviqo_all_records()

    if not records:
        return None

    # Explicit database-count questions
    if (
        ("how many" in q or "count" in q or "number of" in q)
        and ("pci" in q or "i/o" in q or "io" in q)
    ):
        from collections import Counter

        io_counts = Counter(
            str(r.get("io_type") or "UNKNOWN")
            for r in records
        )

        areas = Counter(
            str(r.get("area") or "UNKNOWN")
            for r in records
        )

        return {
            "answer":
                f"The verified PCI database contains {len(records)} I/O records. "
                f"It is read-only and contains no PLC-write or SCADA-control capability.",
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(records),
            "record_count": len(records),
            "io_type_counts": dict(io_counts),
            "area_count": len(areas),
            "records": [],
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }

    # "what instruments are in PCI"
    if (
        ("what instruments" in q)
        or ("which instruments" in q)
        or ("instruments are in pci" in q)
        or ("pci instruments" in q)
    ):
        from collections import Counter

        kinds = Counter()

        for r in records:
            desc = str(r.get("description") or "").lower()
            tag = str(r.get("tag") or "").upper()

            if tag:
                import re
                m = re.match(r"([A-Z]+)", tag)
                if m:
                    kinds[m.group(1)] += 1
                    continue

            if desc:
                kinds[desc] += 1

        return {
            "answer":
                f"The verified PCI database contains {len(records)} I/O records. "
                "ANVI can query them by instrument tag, area, I/O type, PLC address, "
                "panel and terminal block.",
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(records),
            "record_count": len(records),
            "instrument_prefix_counts": dict(kinds),
            "records": [],
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }

    # "tell me about all I/O"
    if (
        ("all i/o" in q)
        or ("all io" in q)
        or ("all pci io" in q)
        or ("show all i/o" in q)
        or ("show all io" in q)
    ):
        from collections import Counter

        io_counts = Counter(
            str(r.get("io_type") or "UNKNOWN")
            for r in records
        )

        panels = Counter(
            str(r.get("panel") or "UNKNOWN")
            for r in records
        )

        areas = Counter(
            str(r.get("area") or "UNKNOWN")
            for r in records
        )

        return {
            "answer":
                f"I found all {len(records)} verified PCI I/O records. "
                f"The database contains {len(areas)} areas and "
                f"{len(io_counts)} I/O categories. "
                "ANVI can drill into any individual tag or area.",
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(records),
            "record_count": len(records),
            "io_type_counts": dict(io_counts),
            "panel_counts": dict(panels),
            "area_count": len(areas),
            "records": records,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
        }

    return None

def answer(question):
    """
    Universal verified PCI conversational entry point.

    Priority:
    1. Exact instrument lookup
    2. Database-wide PCI questions
    3. Existing semantic/conversational engine
    4. Clean failure

    A new explicit instrument question must never inherit
    a previous instrument's context.
    """

    q = str(question or "").strip()

    # --------------------------------------------------------
    # 1. Exact instrument lookup FIRST
    # --------------------------------------------------------
    record = _anviqo_exact_record(q)

    if record:
        return {
            "answer":
                f"I found {record.get('tag','the instrument')} in the verified PCI database. "
                f"It is {record.get('description','an instrument')} "
                f"in {record.get('area','the recorded area')}. "
                f"It is {record.get('io_type','the recorded I/O type')} "
                f"with PLC address {record.get('plc_address','—')}. "
                f"Panel: {record.get('panel','—')}. "
                f"TB: {record.get('tb_name','—')} {record.get('tb_no','')}.",
            "domain": "pci",
            "evidence": "verified PCI database",
            "record": record,
            "count": 1,
            "records": [record],
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "context_tag": record.get("tag"),
            "conversation_context": False,
        }

    # --------------------------------------------------------
    # 2. Database-wide questions
    # --------------------------------------------------------
    summary = _anviqo_summary_answer(q)

    if summary:
        return summary

    # --------------------------------------------------------
    # 3. Existing PCI conversational engine
    # --------------------------------------------------------
    try:
        result = _PCI_ORIGINAL_ANSWER(q)

        # Do not allow old context to masquerade as a fresh exact answer.
        if isinstance(result, dict):
            result.pop("conversation_context", None)

        return result

    except Exception as e:
        return {
            "answer": "I could not answer that PCI question from the verified database.",
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": 0,
            "records": [],
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "error": str(e),
        }


