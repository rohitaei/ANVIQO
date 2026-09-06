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
