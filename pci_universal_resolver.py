import json
import re
from pathlib import Path

DB_PATH = (
    Path(__file__).resolve().parent
    / "database/pci/pci_instrument_database.json"
)


def normalize(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def load_records():
    with open(DB_PATH, encoding="utf-8") as f:
        return json.load(f)["records"]


def _clean(value):
    return str(value or "").strip()


# Signal suffixes are only used to distinguish a signal tag
# from an equipment/base tag. No database tag is invented.
SIGNAL_SUFFIXES = {
    "HEALTHY",
    "CONTROL_ON",
    "EPB",
    "REMOTE_FB",
    "FWD",
    "REV",
    "TRIP_FB",
    "TRQ",
    "OP_FB",
    "CLS_FB",
    "FWD_CMD",
    "REV_CMD",
    "LOCAL_PER",
}


def _is_signal_tag(tag):
    tag = _clean(tag).upper()

    parts = re.split(r"[_\-\s]+", tag)

    if len(parts) < 2:
        return False

    suffix = "_".join(parts[1:])

    return (
        suffix in SIGNAL_SUFFIXES
        or suffix.endswith("_FB")
        or suffix.endswith("_CMD")
    )


def family_keys(record):
    """
    Build only evidence-derived family keys.

    Sources:
      1. fox_plc_tag
      2. actual database tag
      3. verified description containing the same normalized identifier
      4. known signal suffix removal

    No tag is created.
    """

    result = set()

    tag = _clean(record.get("tag"))
    fox = _clean(record.get("fox_plc_tag"))
    desc = _clean(record.get("description"))

    if fox:
        result.add(normalize(fox))

    if tag:
        nt = normalize(tag)
        if nt:
            result.add(nt)

        parts = re.split(r"[_\-\s]+", tag.upper())

        # Example:
        # MCV_203_Healthy -> MCV203
        # MCV_203_FWD_Cmd -> MCV203
        if len(parts) >= 2:
            suffix = "_".join(parts[1:])

            if suffix in SIGNAL_SUFFIXES:
                base = normalize(parts[0] + parts[1])
                if base:
                    result.add(base)

            elif suffix.endswith("_FB") or suffix.endswith("_CMD"):
                base = normalize(parts[0] + parts[1])
                if base:
                    result.add(base)

    # Only use description evidence when it contains an existing
    # database-derived identifier.
    nd = normalize(desc)

    for value in (tag, fox):
        nv = normalize(value)

        if nv and len(nv) >= 3 and nv in nd:
            result.add(nv)

    return {x for x in result if x}


def build_index(records=None):
    records = load_records() if records is None else records

    exact = {}
    families = {}

    for record in records:
        tag = _clean(record.get("tag"))

        if tag:
            exact.setdefault(normalize(tag), []).append(record)

        for key in family_keys(record):
            families.setdefault(key, []).append(record)

    return exact, families


def _dedupe(records):
    """
    Preserve every authoritative record instance while avoiding
    accidental duplicate object references.
    """

    seen = set()
    result = []

    for record in records:
        key = (
            _clean(record.get("tag")),
            _clean(record.get("io_type")),
            _clean(record.get("plc_address")),
            _clean(record.get("panel")),
            _clean(record.get("tb_name")),
            _clean(record.get("tb_no")),
            _clean(record.get("source_sheet")),
            _clean(record.get("description")),
        )

        if key not in seen:
            seen.add(key)
            result.append(record)

    return result


def resolve(query, records=None):
    """
    Universal authoritative PCI resolver.

    Behaviour:

      MCV 203
      MCV-203
      MCV203
      MCV_203

          -> equipment FAMILY when the database proves a family.

      MCV_203_FWD_Cmd
      ZT_203
      AO_203

          -> exact verified tag records.

    Exact records are NEVER invented.
    """

    records = load_records() if records is None else records

    exact, families = build_index(records)

    q = _clean(query)
    nq = normalize(q)

    if not nq:
        return [], None

    # ---------------------------------------------------------------
    # NATURAL-LANGUAGE FAMILY + I/O RESOLUTION
    #
    # Examples:
    #   MCV 204 DO
    #   MCV-204 DO
    #   MCV_204 DO
    #   what is the DO for MCV 204
    #   show me MCV 204 DO
    #   tell me the digital output of MCV 204
    #
    # Resolve only against verified database families.
    # Never invent a tag or I/O point.
    # ---------------------------------------------------------------
    natural_io = re.search(
        r"\b(MCV|PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|FV|XV)"
        r"[\s_-]*(\d+)\b"
        r".{0,60}?\b(DI|DO|AI|AO|DIGITAL\s+INPUT|DIGITAL\s+OUTPUT|"
        r"ANALOG\s+INPUT|ANALOG\s+OUTPUT)\b",
        q,
        flags=re.IGNORECASE,
    )

    natural_io_reverse = re.search(
        r"\b(DI|DO|AI|AO|DIGITAL\s+INPUT|DIGITAL\s+OUTPUT|"
        r"ANALOG\s+INPUT|ANALOG\s+OUTPUT)\b"
        r".{0,60}?\b(MCV|PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|FV|XV)"
        r"[\s_-]*(\d+)\b",
        q,
        flags=re.IGNORECASE,
    )

    if natural_io:
        prefix = natural_io.group(1).upper()
        number = natural_io.group(2)
        io_raw = natural_io.group(3).upper()
    elif natural_io_reverse:
        io_raw = natural_io_reverse.group(1).upper()
        prefix = natural_io_reverse.group(2).upper()
        number = natural_io_reverse.group(3)
    else:
        prefix = number = io_raw = None

    if prefix and number and io_raw:
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

        io_filter = io_map.get(io_raw)
        family_query = f"{prefix}{number}"
        family_query_n = normalize(family_query)

        family_rows = families.get(family_query_n, [])

        if family_rows and len(family_rows) > 1:
            filtered_rows = []

            for row in _dedupe(family_rows):
                actual_io = _clean(row.get("io_type")).upper()

                if io_filter == "AI":
                    if actual_io.startswith("AI"):
                        filtered_rows.append(row)
                elif actual_io == io_filter:
                    filtered_rows.append(row)

            if filtered_rows:
                return filtered_rows, "NATURAL_FAMILY_IO"

    # ---------------------------------------------------------------
    # NATURAL-LANGUAGE FAMILY + I/O RESOLUTION
    #
    # Examples:
    #   MCV 204 DO
    #   MCV-204 DO
    #   MCV_204 DO
    #   what is the DO for MCV 204
    #   show me MCV 204 DO
    #   tell me the digital output of MCV 204
    #
    # Resolve only against verified database families.
    # Never invent a tag or I/O point.
    # ---------------------------------------------------------------
    natural_io = re.search(
        r"\b(MCV|PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|FV|XV)"
        r"[\s_-]*(\d+)\b"
        r".{0,60}?\b(DI|DO|AI|AO|DIGITAL\s+INPUT|DIGITAL\s+OUTPUT|"
        r"ANALOG\s+INPUT|ANALOG\s+OUTPUT)\b",
        q,
        flags=re.IGNORECASE,
    )

    natural_io_reverse = re.search(
        r"\b(DI|DO|AI|AO|DIGITAL\s+INPUT|DIGITAL\s+OUTPUT|"
        r"ANALOG\s+INPUT|ANALOG\s+OUTPUT)\b"
        r".{0,60}?\b(MCV|PT|FT|TT|LT|LIC|PIC|FIC|TIC|AT|FV|XV)"
        r"[\s_-]*(\d+)\b",
        q,
        flags=re.IGNORECASE,
    )

    if natural_io:
        prefix = natural_io.group(1).upper()
        number = natural_io.group(2)
        io_raw = natural_io.group(3).upper()
    elif natural_io_reverse:
        io_raw = natural_io_reverse.group(1).upper()
        prefix = natural_io_reverse.group(2).upper()
        number = natural_io_reverse.group(3)
    else:
        prefix = number = io_raw = None

    if prefix and number and io_raw:
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

        io_filter = io_map.get(io_raw)
        family_query = f"{prefix}{number}"
        family_query_n = normalize(family_query)

        family_rows = families.get(family_query_n, [])

        if family_rows and len(family_rows) > 1:
            filtered_rows = []

            for row in _dedupe(family_rows):
                actual_io = _clean(row.get("io_type")).upper()

                if io_filter == "AI":
                    if actual_io.startswith("AI"):
                        filtered_rows.append(row)
                elif actual_io == io_filter:
                    filtered_rows.append(row)

            if filtered_rows:
                return filtered_rows, "NATURAL_FAMILY_IO"

    # ---------------------------------------------------------------
    # EXPLICIT I/O FAMILY FILTER
    #
    # Equipment family queries:
    #   MCV204       -> complete verified family
    #   MCV204 DI    -> verified DI records only
    #   MCV204 DO    -> verified DO records only
    #   MCV204 AI    -> verified AI records only
    #   MCV204 AO    -> verified AO records only
    #
    # Only apply DI/DO/AI/AO as a filter when the remaining identifier
    # is itself proven to be a multi-record equipment family.
    #
    # This protects exact signal tags such as AO_203 and PT303.
    # ---------------------------------------------------------------
    io_filter = None
    family_query = q

    m = re.match(
        r"^(.+?)\s+(DI|DO|AI|AO)\s*$",
        q,
        flags=re.IGNORECASE,
    )

    if m:
        candidate = _clean(m.group(1))
        candidate_n = normalize(candidate)

        if candidate_n in families and len(families[candidate_n]) > 1:
            io_filter = m.group(2).upper()
            family_query = candidate

    if io_filter:
        family_query_n = normalize(family_query)
        family_rows = families.get(family_query_n, [])

        filtered_rows = [
            row
            for row in _dedupe(family_rows)
            if _clean(row.get("io_type")).upper() == io_filter
        ]

        return filtered_rows, "FAMILY_IO"

    # Explicit complete-family request.
    all_io_match = re.match(
        r"^(.+?)\s+ALL\s+I/?O\s*$",
        q,
        flags=re.IGNORECASE,
    )

    if all_io_match:
        candidate = _clean(all_io_match.group(1))
        candidate_n = normalize(candidate)

        if candidate_n in families and len(families[candidate_n]) > 1:
            return _dedupe(families[candidate_n]), "FAMILY"

    exact_rows = exact.get(nq, [])
    family_rows = families.get(nq, [])

    # IMPORTANT:
    # If the normalized query is an equipment/base identifier and
    # the database proves a multi-record family, return the family.
    #
    # This fixes:
    # MCV_203 -> AO-only record
    # becoming:
    # MCV_203 -> DI + DO + AI + AO family.
    if family_rows and len(family_rows) > 1:

        signal_exact = False

        for row in exact_rows:
            tag = _clean(row.get("tag"))

            if _is_signal_tag(tag):
                signal_exact = True
                break

        if not signal_exact:
            return _dedupe(family_rows), "FAMILY"

    # Exact authoritative tag resolution.
    if exact_rows:
        return _dedupe(exact_rows), "EXACT"

    # Family resolution when query formatting differs.
    candidates = []

    for key, rows in families.items():
        if len(key) >= 3 and key in nq:
            candidates.append(
                (len(key), _dedupe(rows))
            )

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)

        rows = candidates[0][1]

        if rows:
            return rows, "FAMILY"

    # Token-based fallback.
    tokens = [
        normalize(x)
        for x in re.findall(r"[A-Za-z0-9]+", q)
        if normalize(x)
    ]

    if len(tokens) >= 2:
        compact = "".join(tokens)

        if compact in families:
            rows = _dedupe(families[compact])

            if rows:
                return rows, "FAMILY"

    return [], None


def family_records(query, records=None):
    """
    Return the complete authoritative PCI family for an equipment
    query, or the exact verified records for a signal tag.
    """

    rows, match_type = resolve(query, records)

    if not rows:
        return []

    return rows


def all_records_for_tag(query, records=None):
    """
    Explicit complete verified PCI coverage alias.
    """

    return family_records(query, records)


def group_io(records):
    groups = {
        "DI": [],
        "DO": [],
        "AI": [],
        "AO": [],
        "OTHER": [],
    }

    for record in records:
        io = _clean(record.get("io_type")).upper()

        if io.startswith("AI"):
            groups["AI"].append(record)

        elif io == "DI":
            groups["DI"].append(record)

        elif io == "DO":
            groups["DO"].append(record)

        elif io == "AO":
            groups["AO"].append(record)

        else:
            groups["OTHER"].append(record)

    return groups


def io_summary(query, records=None):
    rows = family_records(query, records)
    groups = group_io(rows)

    return {
        "query": str(query or ""),
        "record_count": len(rows),
        "match": resolve(query, records)[1] if rows else None,
        "DI": groups["DI"],
        "DO": groups["DO"],
        "AI": groups["AI"],
        "AO": groups["AO"],
        "OTHER": groups["OTHER"],
    }
