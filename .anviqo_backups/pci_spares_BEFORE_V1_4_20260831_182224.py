"""
ANVIQO CRITICAL SPARES INTELLIGENCE V1.3
========================================

Authoritative current inventory:
    database/spares/critical_spares.xlsx

V1.3 capabilities:
- Universal spare search
- PT / FT / LT / MCV / RTD / SOV / FSV-PCV / POS'R /
  Analyser / Load Cell / Air Compressor / General
- Available
- Zero stock
- Below required quantity
- Sufficient stock
- Spare-to-indent intelligence
- Shortage intelligence
- Equipment/spare relationship
- Exact tag search
- Excel remains authoritative
- No PLC write
- No SCADA control

IMPORTANT:
This module is READ/ANALYSIS ONLY.
Direct ADD / REMOVE / USED / RECEIVED commands remain in:
    pci_spare_direct_excel.py
"""

from pathlib import Path
import re
import openpyxl

ROOT = Path(__file__).resolve().parent
XLSX = ROOT / "database" / "spares" / "critical_spares.xlsx"


# ============================================================
# SHEET / FAMILY ALIASES
# ============================================================

SHEET_ALIASES = {
    "RTD": {
        "rtd", "thermocouple", "temperature",
        "temperature sensor", "temperature element",
        "pt100", "te"
    },
    "LT": {
        "lt", "level", "level transmitter",
        "level sensor", "radar level", "radar"
    },
    "PT": {
        "pt", "pressure", "pressure transmitter",
        "pressure sensor", "pressure instrument"
    },
    "FT": {
        "ft", "flow", "flow transmitter",
        "flow sensor", "flow meter", "flowmeter"
    },
    "MCV": {
        "mcv", "motorized control valve",
        "motorized valve"
    },
    "FSV&PCV": {
        "fsv", "pcv", "shut off valve",
        "shutoff valve", "pneumatic valve"
    },
    "SOV": {
        "sov", "solenoid", "solenoid valve"
    },
    "POS'R": {
        "positioner", "posr", "pos'r"
    },
    "LOAD CELL": {
        "load cell", "loadcell",
        "encoder", "jam switch", "coal flow meter"
    },
    "Analyser": {
        "analyser", "analyzer",
        "gas analyser", "gas analyzer"
    },
    "AIR COMPRESSOR": {
        "air compressor", "compressor"
    },
    "Sheet1": {
        "general", "normal", "spares", "general spare"
    },
}


# ============================================================
# NORMALIZATION
# ============================================================

def _text(v):
    return str(v or "").strip()


def _norm(v):
    return re.sub(r"[^A-Z0-9]+", "", _text(v).upper())


def _qty_num(v):
    if v is None or v == "":
        return None

    if isinstance(v, (int, float)):
        return float(v)

    text = _text(v).replace(",", "")

    # Examples:
    # "3"
    # "3 nos"
    # "2 BOX"
    m = re.search(r"-?\d+(?:\.\d+)?", text)

    if not m:
        return None

    try:
        return float(m.group(0))
    except Exception:
        return None


def _fmt_qty(v):
    n = _qty_num(v)

    if n is None:
        return "not recorded"

    if float(n).is_integer():
        return str(int(n))

    return f"{n:g}"


# ============================================================
# HEADER DETECTION
# ============================================================

def _find_header_row(ws):
    """
    Find the real column-header row.

    Many workbook sheets contain a title row first.
    Example:

        Row 1 = SPARES FOR PR
        Row 2 = SL.NO / INSTRUMENT / Qty Req / TAG NO ...

    V1.3 therefore scans the first several rows.
    """

    best_row = None
    best_score = -1

    header_terms = {
        "tag no",
        "tag",
        "description",
        "short description",
        "instrument",
        "specification",
        "qty avbl",
        "qty",
        "qty req",
        "spare to be indent",
        "installation site",
        "instalation site",
        "location",
        "item",
    }

    for row_no in range(1, min(ws.max_row, 8) + 1):

        values = [
            _text(c.value).lower()
            for c in ws[row_no]
        ]

        score = 0

        for value in values:
            if value in header_terms:
                score += 2
            elif any(term in value for term in header_terms):
                score += 1

        if score > best_score:
            best_score = score
            best_row = row_no

    return best_row if best_score > 0 else 1


def _header_map(ws, header_row):
    result = {}

    for col in range(1, ws.max_column + 1):
        value = _text(ws.cell(header_row, col).value)

        if value:
            result[_norm(value)] = col

    return result


def _get_col(headers, *names):
    for name in names:
        key = _norm(name)

        if key in headers:
            return headers[key]

    return None


# ============================================================
# REQUIRED / AVAILABLE QUANTITY
# ============================================================

def _get_required(d):
    """
    Required quantity.

    Different sheets use:
      Qty Req
      Qty
      Spare to be indent

    Required quantity is the installed spare requirement.
    """

    for key in (
        "qty req",
        "required quantity",
        "required",
        "qty required",
    ):
        if key in d:
            q = _qty_num(d[key])

            if q is not None:
                return q

    return None


def _get_available(d):
    for key in (
        "qty avbl",
        "qty available",
        "available",
        "qty",
    ):
        if key in d:
            q = _qty_num(d[key])

            if q is not None:
                return q

    return None


def _get_indent(d):
    for key in (
        "spare to be indent",
        "spare to indent",
        "indent",
    ):
        if key in d:
            q = _qty_num(d[key])

            if q is not None:
                return q

    return None


def _calculate_status(available, required):
    """
    Stock status:

      ZERO STOCK
      BELOW REQUIRED
      SUFFICIENT STOCK
      STOCK NOT RECORDED
    """

    if available is None:
        return "STOCK NOT RECORDED"

    if available <= 0:
        return "ZERO STOCK"

    if required is not None and available < required:
        return "BELOW REQUIRED"

    return "SUFFICIENT STOCK"


def _calculate_indent(available, required, recorded_indent):
    """
    Calculate shortage independently of possibly stale Excel formulas.

    If:
        required = 3
        available = 1

    then:
        indent = 2
    """

    if available is not None and required is not None:

        shortage = required - available

        if shortage > 0:
            return shortage

        return 0

    if recorded_indent is not None:
        return recorded_indent

    return None


# ============================================================
# ROW PARSER
# ============================================================

def _parse_row(headers, values, sheet, row_no):

    d = {}

    for col_no, value in enumerate(values, start=1):

        if col_no > len(headers):
            continue

        header = _text(headers[col_no - 1])

        if not header:
            continue

        d[header.lower().strip()] = value

    tag = (
        d.get("tag no")
        or d.get("tag")
        or d.get("tag no.")
    )

    instrument = (
        d.get("instrument")
        or d.get("short description")
        or d.get("item")
        or d.get("description")
    )

    description = (
        d.get("description")
        or d.get("item")
        or d.get("short description")
    )

    specification = (
        d.get("specification")
        or d.get("description")
    )

    location = (
        d.get("instalation site")
        or d.get("installation site")
        or d.get("location")
    )

    available = _get_available(d)
    required = _get_required(d)
    recorded_indent = _get_indent(d)

    calculated_indent = _calculate_indent(
        available,
        required,
        recorded_indent
    )

    status = _calculate_status(
        available,
        required
    )

    # Reject obvious title/header artefacts.
    tag_text = _text(tag)

    if tag_text.lower() in {
        "tag no",
        "tag",
        "short description",
        "description",
        "specification",
        "spare to be indent",
    }:
        tag = ""

    return {
        "sheet": sheet,
        "row": row_no,

        "tag": _text(tag),
        "instrument": _text(instrument),
        "description": _text(description),
        "specification": _text(specification),
        "location": _text(location),

        "qty_available": available,
        "qty_required": required,

        "spare_to_indent_recorded": recorded_indent,
        "spare_to_indent": calculated_indent,

        "status": status,

        "raw": d,
    }


# ============================================================
# LOAD WORKBOOK
# ============================================================

def load_spares():
    """
    Efficient single-pass Excel loader.

    IMPORTANT:
    Excel remains the authoritative current inventory.

    The workbook is opened in read-only mode and each worksheet is
    streamed row-by-row. Avoid ws.cell() because openpyxl read-only
    mode can repeatedly scan the worksheet XML when random-access
    cell reads are used.
    """

    if not XLSX.exists():
        return []

    rows = []

    wb = openpyxl.load_workbook(
        XLSX,
        data_only=True,
        read_only=True
    )

    try:
        for sheet in wb.sheetnames:

            ws = wb[sheet]

            # Read the worksheet sequentially.
            iterator = ws.iter_rows(
                values_only=True
            )

            header_row = None
            headers = None

            # Find the header within the first 10 rows.
            for row_no, values in enumerate(iterator, start=1):

                values = tuple(values)

                header_text = " ".join(
                    _text(x).lower()
                    for x in values
                    if x is not None
                )

                if any(
                    x in header_text
                    for x in (
                        "tag no",
                        "tag",
                        "description",
                        "short description",
                        "instrument",
                        "specification",
                        "item",
                        "qty",
                    )
                ):
                    header_row = row_no
                    headers = values
                    break

                if row_no >= 10:
                    break

            if header_row is None:
                continue

            # Stream remaining rows.
            for row_no, values in enumerate(
                iterator,
                start=header_row + 1
            ):

                values = tuple(values)

                if not any(
                    v not in (None, "")
                    for v in values
                ):
                    continue

                rec = _parse_row(
                    headers,
                    values,
                    sheet,
                    row_no
                )

                # Ignore blank/header-only records.
                if not any([
                    rec["tag"],
                    rec["instrument"],
                    rec["description"],
                    rec["specification"],
                ]):
                    continue

                combined = " ".join([
                    rec["tag"],
                    rec["instrument"],
                    rec["description"],
                ]).lower()

                if (
                    "qty avbl" in combined
                    or "spare to be indent" in combined
                    or combined.strip() == "short description"
                ):
                    continue

                rows.append(rec)

    finally:
        wb.close()

    return rows


# ============================================================
# FAMILY DETECTION
# ============================================================

def _sheet_hint(q):

    ql = _text(q).lower()

    rules = [
        ("FSV&PCV", (
            "fsv",
            "pcv",
            "shut off valve",
            "shutoff valve",
            "pneumatic valve",
        )),

        ("AIR COMPRESSOR", (
            "air compressor",
            "compressor spare",
            "compressor spares",
        )),

        ("LOAD CELL", (
            "load cell",
            "loadcell",
            "coal flow meter",
            "jam switch",
        )),

        ("Analyser", (
            "analyser",
            "analyzer",
            "gas analyser",
            "gas analyzer",
        )),

        ("POS'R", (
            "positioner",
            "pos'r",
            "posr",
        )),

        ("MCV", (
            "mcv",
            "motorized control valve",
            "motorized valve",
        )),

        ("SOV", (
            "sov",
            "solenoid valve",
            "solenoid",
        )),

        ("RTD", (
            "rtd",
            "pt100",
            "temperature transmitter",
            "temperature sensor",
            "temperature element",
        )),

        ("LT", (
            "lt transmitter",
            "level transmitter",
            "level sensor",
            "radar level",
        )),

        ("PT", (
            "pt transmitter",
            "pressure transmitter",
            "pressure sensor",
            "pressure instrument",
        )),

        ("FT", (
            "ft transmitter",
            "flow transmitter",
            "flow sensor",
            "flow meter",
            "flowmeter",
        )),
    ]

    for sheet, phrases in rules:

        for phrase in phrases:

            if phrase in ql:
                return sheet

    tag_pattern = re.compile(
        r"\b"
        r"(MCV|PT|FT|LT|RTD|TE|SOV|FSV|PCV)"
        r"[-_ ]?\d+[A-Z]?"
        r"\b",
        re.IGNORECASE
    )

    match = tag_pattern.search(q)

    if match:

        prefix = match.group(1).upper()

        return {
            "MCV": "MCV",
            "PT": "PT",
            "FT": "FT",
            "LT": "LT",
            "RTD": "RTD",
            "TE": "RTD",
            "SOV": "SOV",
            "FSV": "FSV&PCV",
            "PCV": "FSV&PCV",
        }.get(prefix)

    return None


# ============================================================
# EXACT TAG SEARCH
# ============================================================

def _extract_tag(q):

    pattern = re.compile(
        r"\b"
        r"(MCV|PT|FT|LT|RTD|TE|SOV|FSV|PCV)"
        r"[-_ ]?\d+[A-Z]?"
        r"\b",
        re.IGNORECASE
    )

    match = pattern.search(q)

    if not match:
        return None

    return match.group(0)


# ============================================================
# UNIVERSAL SEARCH
# ============================================================

def search_spares(query, limit=50):

    q = _text(query)
    ql = q.lower()

    rows = load_spares()

    if not rows:
        return []

    # --------------------------------------------------------
    # EXACT TAG ALWAYS GETS PRIORITY
    # --------------------------------------------------------

    explicit_tag = _extract_tag(q)

    if explicit_tag:

        target = _norm(explicit_tag)

        exact = [
            r for r in rows
            if _norm(r.get("tag")) == target
        ]

        if exact:
            return exact[:limit]

    # --------------------------------------------------------
    # FAMILY FILTER
    # --------------------------------------------------------

    sheet_hint = _sheet_hint(q)

    candidates = rows

    if sheet_hint:

        candidates = [
            r for r in candidates
            if r["sheet"] == sheet_hint
        ]

    # --------------------------------------------------------
    # STOCK INTENT
    # --------------------------------------------------------

    available_only = any(
        x in ql
        for x in (
            "available spare",
            "available spares",
            "available",
            "in stock",
            "stock available",
            "currently available",
            "sufficient stock",
        )
    )

    zero_only = any(
        x in ql
        for x in (
            "zero stock",
            "zero stocks",
            "out of stock",
            "no stock",
            "not available",
        )
    )

    below_only = any(
        x in ql
        for x in (
            "below required",
            "below requirement",
            "short",
            "shortage",
            "short spares",
            "which spares are short",
        )
    )

    indent_only = any(
        x in ql
        for x in (
            "to indent",
            "spares to indent",
            "spare to indent",
            "show spares to indent",
            "indent",
        )
    )

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    if indent_only or below_only:

        filtered = []

        for r in candidates:

            available = r["qty_available"]
            required = r["qty_required"]

            if (
                available is not None
                and required is not None
                and available < required
            ):
                filtered.append(r)

            elif (
                indent_only
                and r["spare_to_indent"] is not None
                and r["spare_to_indent"] > 0
            ):
                if r not in filtered:
                    filtered.append(r)

        candidates = filtered

    elif zero_only:

        candidates = [
            r for r in candidates
            if (
                r["qty_available"] is not None
                and r["qty_available"] <= 0
            )
        ]

    elif available_only:

        candidates = [
            r for r in candidates
            if (
                r["qty_available"] is not None
                and r["qty_available"] > 0
            )
        ]

    # --------------------------------------------------------
    # GENERIC SEARCH
    # --------------------------------------------------------

    stop = {
        "ANVI",
        "SHOW",
        "ME",
        "WHAT",
        "WHICH",
        "THE",
        "FOR",
        "OF",
        "A",
        "AN",
        "IS",
        "ARE",
        "WE",
        "HAVE",
        "SPARE",
        "SPARES",
        "CRITICAL",
        "AVAILABLE",
        "CURRENTLY",
        "STOCK",
        "IN",
        "OUT",
        "TO",
        "BE",
        "MY",
        "DO",
        "DOES",
    }

    tokens = []

    for token in re.findall(
        r"[A-Za-z0-9_-]+",
        q
    ):

        normalized = _norm(token)

        if normalized and normalized not in stop:
            tokens.append(normalized)

    # If query is purely a stock-status query, return filtered rows.
    if not tokens:

        return candidates[:limit]

    scored = []

    for r in candidates:

        searchable = _norm(" ".join([
            r["tag"],
            r["instrument"],
            r["description"],
            r["specification"],
            r["location"],
        ]))

        score = 0

        for token in tokens:

            if token in searchable:
                score += 2

        if score > 0:

            scored.append(
                (score, r)
            )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        r
        for _, r in scored[:limit]
    ]


# ============================================================
# RESPONSE FORMAT
# ============================================================

def _format_record(r):

    text = (
        f"{r['tag'] or r['instrument'] or 'Spare'}"
        f" — {r['instrument'] or r['description'] or 'Spare instrument'}"
        f"; Location: {r['location'] or 'not recorded'}"
        f"; Available: {_fmt_qty(r['qty_available'])}"
        f"; Required: {_fmt_qty(r['qty_required'])}"
        f"; Status: {r['status']}"
        f"; Spare to indent: {_fmt_qty(r['spare_to_indent'])}"
        f"; Sheet: {r['sheet']}; Row: {r['row']}."
    )

    if r["specification"]:
        text += f"\nSpecification: {r['specification']}"

    return text


# ============================================================
# NATURAL LANGUAGE SPARE QUERY
# ============================================================

def answer_spare_query(question):

    q = _text(question)
    ql = q.lower()

    rows = load_spares()

    if not rows:

        return {
            "domain": "critical_spares",
            "answer": (
                "ANVI could not find any spare inventory records "
                "in critical_spares.xlsx."
            ),
            "evidence": "critical_spares.xlsx",
        }

    results = search_spares(q, limit=50)

    # --------------------------------------------------------
    # EXACT TAG CURRENT QUANTITY
    # --------------------------------------------------------

    explicit_tag = _extract_tag(q)

    if explicit_tag and results:

        r = results[0]

        answer = (
            "ANVI found 1 verified critical spare instrument record(s). "
            "Source: critical spares in pci.xlsx.\n"
            + _format_record(r)
        )

        return {
            "domain": "critical_spares",
            "answer": answer,
            "evidence": "critical_spares.xlsx",
        }

    # --------------------------------------------------------
    # INDENT / SHORTAGE
    # --------------------------------------------------------

    if (
        "to indent" in ql
        or "spares to indent" in ql
        or "which spares are short" in ql
        or "which spares are short" in ql
        or "short spares" in ql
        or "shortage" in ql
    ):

        if not results:

            return {
                "domain": "critical_spares",
                "answer": (
                    "ANVI found no verified spare records currently "
                    "below the required quantity."
                ),
                "evidence": "critical_spares.xlsx",
            }

        lines = [
            "ANVI found "
            f"{len(results)} spare record(s) requiring attention.",
            "Source: critical spares in pci.xlsx.",
            "",
        ]

        for r in results:

            lines.append(
                _format_record(r)
            )

        return {
            "domain": "critical_spares",
            "answer": "\n".join(lines),
            "evidence": "critical_spares.xlsx",
        }

    # --------------------------------------------------------
    # NORMAL FAMILY SEARCH
    # --------------------------------------------------------

    if results:

        lines = [
            f"ANVI found {len(results)} verified critical spare "
            "instrument record(s).",
            "Source: critical spares in pci.xlsx.",
            "",
        ]

        for r in results:
            lines.append(
                _format_record(r)
            )

        return {
            "domain": "critical_spares",
            "answer": "\n".join(lines),
            "evidence": "critical_spares.xlsx",
        }

    # --------------------------------------------------------
    # NOTHING FOUND
    # --------------------------------------------------------

    return {
        "domain": "critical_spares",
        "answer": (
            "ANVI could not find a matching spare record in "
            "critical_spares.xlsx."
        ),
        "evidence": "critical_spares.xlsx",
    }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("ANVIQO V1.3 SPARE INTELLIGENCE AUDIT")
    print("=" * 70)

    records = load_spares()

    print("TOTAL PARSED RECORDS:", len(records))

    for status in (
        "SUFFICIENT STOCK",
        "BELOW REQUIRED",
        "ZERO STOCK",
        "STOCK NOT RECORDED",
    ):

        count = sum(
            1
            for r in records
            if r["status"] == status
        )

        print(f"{status:22}: {count}")

    print()
    print("PT-303 TEST")

    result = search_spares(
        "what spare is available for PT-303",
        limit=5
    )

    for r in result:
        print(_format_record(r))

    print()
    print("MCV TEST")

    result = search_spares(
        "show spares for MCV",
        limit=20
    )

    for r in result:
        print(_format_record(r))

    print()
    print("INDENT TEST")

    result = search_spares(
        "show spares to indent",
        limit=50
    )

    print("SHORT RECORDS:", len(result))

    for r in result:
        print(_format_record(r))

    print()
    print("===== V1.3 READ AUDIT COMPLETE =====")
