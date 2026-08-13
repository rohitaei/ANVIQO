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


def _find_tag_in_question(q):
    # Exact database tag detection first.
    q_upper = q.upper()

    for r in search(query=None, limit=1064):
        tag = str(r.get("tag", "")).strip()

        if tag:
            # Match the complete PCI tag only.
            # Prevent short tags such as "DO" from matching
            # ordinary words such as "does".
            pattern = r"(?<![A-Z0-9_])" + re.escape(tag.upper()) + r"(?![A-Z0-9_])"
            if re.search(pattern, q_upper):
                return r

    # Follow-up: "it", "this instrument", "that instrument", etc.
    # Follow-up references must be matched as words/phrases.
    # IMPORTANT: do not use substring matching for "it".
    # Otherwise words such as "critical", "instruments" and
    # "transmitters" incorrectly trigger the previous record.
    followup_phrases = [
        "this instrument",
        "that instrument",
        "this tag",
        "that tag",
        "this io",
        "that io",
        "what is it",
        "what does it",
        "what does it measure",
        "what is it measuring",
        "tell me about it",
        "its area",
        "its location",
        "where is it",
        "where is it located",
        "its plc address",
        "its panel",
        "its terminal",
        "its tb",
        "its status",
        "its state",
        "its value",
        "what value",
        "what reading",
        "what is the reading",
        "is it healthy",
        "is it critical",
        "why is it critical",
        "why is it healthy",
        "what event",
        "what event is active",
        "is there an event",
        "what does this mean",
    ]

    if any(phrase in q.lower() for phrase in followup_phrases):
        return _CONTEXT.get("last_record")

    if re.search(r"\bit\b", q.lower()):
        return _CONTEXT.get("last_record")

    return None


def answer(question):
    q = (question or "").strip()
    ql = q.lower()

    if not q:
        return {
            "answer": "Please ask me about a PCI instrument, signal, area or I/O.",
            "domain": "pci",
            "read_only": True,
        }

    record = _find_tag_in_question(q)

    # --------------------------------------------------------
    # Exact instrument / follow-up
    # --------------------------------------------------------
    if record:

        _remember(record=record)

        if (
            "plc address" in ql
            or "plc address" in ql
            or "address" in ql
        ):
            return {
                "answer": (
                    f"The PLC address for {record.get('tag')} is "
                    f"{record.get('plc_address') or 'not specified in the source record'}."
                ),
                "domain": "pci",
                "evidence": "verified PCI database",
                "record": compact(record),
                "read_only": True,
            }

        if "panel" in ql:
            return {
                "answer": (
                    f"{record.get('tag')} is mapped to panel "
                    f"{record.get('panel') or 'not specified in the source record'}."
                ),
                "domain": "pci",
                "evidence": "verified PCI database",
                "record": compact(record),
                "read_only": True,
            }

        if (
            "tb" in ql
            or "terminal" in ql
            or "termination" in ql
            or "terminate" in ql
        ):
            return {
                "answer": (
                    f"{record.get('tag')} is associated with TB "
                    f"{record.get('tb_name') or 'not specified'}"
                    f" and terminal reference "
                    f"{record.get('tb_no') or 'not specified'}."
                ),
                "domain": "pci",
                "evidence": "verified PCI database",
                "record": compact(record),
                "read_only": True,
            }

        if "area" in ql or "where" in ql or "location" in ql:
            return {
                "answer": (
                    f"{record.get('tag')} is in "
                    f"{record.get('area') or 'an area not specified in the source record'}. "
                    f"It is described as {record.get('description') or 'no description available'}."
                ),
                "domain": "pci",
                "evidence": "verified PCI database",
                "record": compact(record),
                "read_only": True,
            }

        # --------------------------------------------------------
        # Measurement / description follow-up
        # --------------------------------------------------------
        if (
            "what does it measure" in ql
            or "what is it measuring" in ql
            or "what does this measure" in ql
        ):
            description = record.get("description")

            if description:
                answer_text = (
                    f"The verified PCI description for {record.get('tag')} is "
                    f"'{description}'. The PCI source does not specify a "
                    "separate engineering unit or measurement range."
                )
            else:
                answer_text = (
                    f"The verified PCI database does not specify what "
                    f"{record.get('tag')} measures."
                )

            return {
                "answer": answer_text,
                "domain": "pci",
                "evidence": "verified PCI database",
                "record": compact(record),
                "read_only": True,
            }

        # --------------------------------------------------------
        # Critical-state explanation
        # --------------------------------------------------------
        if "why is it critical" in ql or "why is this critical" in ql:
            live = _live_point(record.get("tag"))

            if live and live.get("state") == "CRITICAL":
                answer_text = (
                    f"{record.get('tag')} is currently marked CRITICAL in "
                    "the PCI DEMO SIMULATION. The simulator provides the "
                    "current state and simulated value, but it does not "
                    "contain a verified cause for the critical condition. "
                    "I won't invent a cause."
                )
            else:
                answer_text = (
                    f"{record.get('tag')} is not currently marked CRITICAL "
                    "in the PCI DEMO SIMULATION."
                )

            return {
                "answer": answer_text,
                "domain": "pci",
                "evidence": "PCI DEMO SIMULATION",
                "record": compact(record),
                "simulation": live,
                "read_only": True,
            }


        # --------------------------------------------------------
        # Current simulation state / health
        # --------------------------------------------------------
        if (
            "is it healthy" in ql
            or "is it critical" in ql
            or "its status" in ql
            or "its state" in ql
            or "is it working" in ql
            or "its condition" in ql
        ):
            live = _live_point(record.get("tag"))

            return {
                "answer": _state_sentence(live),
                "domain": "pci",
                "evidence": "PCI DEMO SIMULATION",
                "record": compact(record),
                "simulation": live,
                "read_only": True,
            }

        # --------------------------------------------------------
        # Event follow-up
        # --------------------------------------------------------
        if "what event is active" in ql or "is there an event" in ql:
            live = _live_point(record.get("tag"))

            if live and live.get("event_active"):
                answer_text = (
                    f"The PCI DEMO SIMULATION currently marks an "
                    f"associated event as active for {record.get('tag')}. "
                    "The simulator does not provide an event description "
                    "or verified cause."
                )
            else:
                answer_text = (
                    f"No active associated event is currently reported "
                    f"for {record.get('tag')} by the PCI DEMO SIMULATION."
                )

            return {
                "answer": answer_text,
                "domain": "pci",
                "evidence": "PCI DEMO SIMULATION",
                "record": compact(record),
                "simulation": live,
                "read_only": True,
            }

        live = _live_point(record.get("tag"))

        state_text = _state_sentence(live)

        return {
            "answer": (
                f"I found {record.get('tag')} in the verified PCI database. "
                f"It is {record.get('description') or 'not described'} "
                f"in {record.get('area') or 'an unspecified area'}. "
                f"It is {record.get('io_type') or 'an unspecified I/O type'} "
                f"with PLC address {record.get('plc_address') or 'not specified'}. "
                f"Panel: {record.get('panel') or 'not specified'}. "
                f"TB: {record.get('tb_name') or 'not specified'} "
                f"{record.get('tb_no') or ''}. "
                f"{state_text}"
            ),
            "domain": "pci",
            "evidence": "verified PCI database + PCI DEMO SIMULATION",
            "record": compact(record),
            "simulation": live,
            "read_only": True,
        }

    # --------------------------------------------------------
    # Area search
    # --------------------------------------------------------
    if (
        "vrm / mill" in ql
        or "vrm/mill" in ql
        or "vrm mill" in ql
    ):
        results = search_area("VRM / MILL", limit=1064)
        _remember(results=results)

        return {
            "answer": (
                f"I found {len(results)} verified PCI records in VRM / MILL. "
                "I can narrow them by transmitter, valve, I/O type, tag or process role."
            ),
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(results),
            "records": [compact(r) for r in results],
            "read_only": True,
        }

    # --------------------------------------------------------
    # Pressure transmitters
    # --------------------------------------------------------
    if (
        "pressure transmitter" in ql
        or "pressure transmitters" in ql
    ):
        results = search_pressure_transmitters(limit=1064)
        _remember(results=results)

        return {
            "answer": (
                f"I found {len(results)} pressure-transmitter records "
                "in the verified PCI database."
            ),
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(results),
            "records": [compact(r) for r in results],
            "read_only": True,
        }

    # --------------------------------------------------------
    # Critical instruments
    # --------------------------------------------------------
    if "critical" in ql:
        results = search_critical(limit=1064)
        _remember(results=results)

        return {
            "answer": (
                f"I found {len(results)} PCI records explicitly classified "
                "HIGH criticality in the source database."
            ),
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(results),
            "records": [compact(r) for r in results],
            "read_only": True,
        }

    # --------------------------------------------------------
    # State-aware follow-up
    # --------------------------------------------------------
    if (
        record is not None
        and (
            "healthy" in ql
            or "status" in ql
            or "state" in ql
            or "changed" in ql
            or "working" in ql
            or "condition" in ql
            or "event" in ql
        )
    ):
        live = _live_point(record.get("tag"))

        return {
            "answer": _state_sentence(live),
            "domain": "pci",
            "evidence": "PCI DEMO SIMULATION",
            "record": compact(record),
            "simulation": live,
            "read_only": True,
        }

    # --------------------------------------------------------
    # Generic PCI search
    # --------------------------------------------------------
    results = search(query=q, limit=100)

    if results:
        _remember(results=results)

        preview = results[:10]

        return {
            "answer": (
                f"I found {len(results)} matching PCI records in the "
                "verified database. Here are the first "
                f"{len(preview)} matches."
            ),
            "domain": "pci",
            "evidence": "verified PCI database",
            "count": len(results),
            "records": [compact(r) for r in preview],
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
        "read_only": True,
    }
