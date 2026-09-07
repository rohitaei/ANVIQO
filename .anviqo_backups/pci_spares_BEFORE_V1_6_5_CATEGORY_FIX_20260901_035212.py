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


# ================================================================
# ANVIQO CRITICAL SPARES V1.4 — UNIVERSAL QUERY LAYER
# Appended intentionally: preserves existing inventory mutation/audit logic.
# Read-only query path. No PLC write. No SCADA control.
# ================================================================

_STATUS_STOP = {
    "ANVI", "THE", "FOR", "OF", "A", "AN", "IS", "ARE", "WE", "HAVE",
    "DOES", "DO", "SHOW", "ME", "TELL", "WHAT", "ABOUT", "WHICH", "LIST",
    "ALL", "CRITICAL", "SPARE", "SPARES", "STOCK", "STATUS", "AVAILABLE",
    "AVAILABILITY", "INSTRUMENT", "INSTRUMENTS", "RECORD", "RECORDS",
    "ITEM", "ITEMS", "THERE", "ANY", "CAN", "YOU", "GIVE", "US"
}


def _v14_num(v):
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(v)
    except Exception:
        return None


def _v14_clean(v):
    return str(v or "").strip()


def _v14_norm(v):
    import re as _re
    return _re.sub(r"[^A-Z0-9]+", "", str(v or "").upper())


def _v14_header_map(row):
    """Map messy Excel headers to canonical names."""
    out = {}
    for i, h in enumerate(row):
        k = _v14_norm(h)
        if k:
            out[k] = i
    return out


def _v14_pick(vals, hm, *names):
    for name in names:
        i = hm.get(_v14_norm(name))
        if i is not None and i < len(vals):
            v = vals[i]
            if v not in (None, ""):
                return v
    return None


def _v14_load_spares():
    """Robust workbook reader; skips repeated header rows and title rows."""
    import openpyxl
    xlsx = globals().get("XLSX", ROOT / "database" / "spares" / "critical_spares.xlsx")
    if not xlsx.exists():
        return []
    wb = openpyxl.load_workbook(xlsx, data_only=True, read_only=True)
    rows = []
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            continue
        # A sheet can contain more than one table (SOV is an example).
        header_indexes = []
        for i, r in enumerate(all_rows):
            hm = _v14_header_map(r)
            keys = set(hm)
            has_qty = any(k in keys for k in ("QTYAVBL", "QTY", "AVAILABLE"))
            has_identity = any(k in keys for k in ("TAGNO", "TAG", "SHORTDESCRIPTION", "INSTRUMENT", "DESCRIPTION", "ITEM"))
            if has_qty and has_identity:
                header_indexes.append(i)
        if not header_indexes:
            continue
        for hi, header_idx in enumerate(header_indexes):
            end = header_indexes[hi + 1] if hi + 1 < len(header_indexes) else len(all_rows)
            headers = all_rows[header_idx]
            hm = _v14_header_map(headers)
            for idx in range(header_idx + 1, end):
                vals = all_rows[idx]
                if not any(v not in (None, "") for v in vals):
                    continue
                # Never turn a repeated header into a spare record.
                text = " ".join(_v14_clean(v).lower() for v in vals if v not in (None, ""))
                if "short description" in text and ("qty avbl" in text or "qty" in text):
                    continue
                tag = _v14_pick(vals, hm, "TAG NO", "TAG NO.", "TAG")
                instrument = _v14_pick(vals, hm, "INSTRUMENT", "SHORT DESCRIPTION")
                item = _v14_pick(vals, hm, "ITEM")
                description = _v14_pick(vals, hm, "DESCRIPTION")
                spec = _v14_pick(vals, hm, "SPECIFICATION")
                location = _v14_pick(vals, hm, "INSTALATION SITE", "INSTALLATION SITE", "LOCATION")
                qty = _v14_pick(vals, hm, "QTY AVBL", "QTY", "AVAILABLE", "QTY ")
                required = _v14_pick(vals, hm, "QTY REQ", "QTY REQUIRED", "REQUIRED")
                indent = _v14_pick(vals, hm, "SPARE TO BE INDENT", "SPARE TO INDENT")
                # For Sheet1/general inventory there is no required column.
                if sheet == "Sheet1":
                    if not description:
                        description = _v14_pick(vals, hm, "DESCRIPTION", "ITEM")
                    if qty is None:
                        qty = _v14_pick(vals, hm, "QTY")
                identity = tag or instrument or item or description or spec
                if not identity:
                    continue
                # The source SOV sheet contains a second positioner table;
                # those records belong to POS'R and must not be reported as SOV.
                if sheet == "SOV" and "POSITIONER" in _v14_norm(instrument):
                    continue
                qn = _v14_num(qty)
                rn = _v14_num(required)
                if qn is None:
                    status = "STOCK NOT RECORDED"
                elif rn is not None and qn <= 0:
                    status = "ZERO STOCK"
                elif rn is not None and qn < rn:
                    status = "BELOW REQUIRED"
                elif rn is not None and qn >= rn:
                    status = "SUFFICIENT STOCK"
                elif qn > 0:
                    status = "STOCK AVAILABLE"
                else:
                    status = "ZERO STOCK"
                rows.append({
                    "sheet": sheet,
                    "row": idx + 1,
                    "tag": _v14_clean(tag),
                    "instrument": _v14_clean(instrument),
                    "item": _v14_clean(item),
                    "description": _v14_clean(description),
                    "specification": _v14_clean(spec),
                    "location": _v14_clean(location),
                    "qty_available": qty,
                    "qty_required": required,
                    "spare_to_indent": indent,
                    "status": status,
                    "raw": {str(i): v for i, v in enumerate(vals) if v not in (None, "")},
                })
    return rows


def _v14_sheet_hint(q):
    qn = _v14_norm(q)
    aliases = {
        "RTD": {"RTD", "THERMOCOUPLE", "TEMPERATURE", "TE"},
        "LT": {"LT", "LEVEL", "LEVELTRANSMITTER", "RADAR", "LE"},
        "PT": {"PT", "PRESSURE", "PRESSURETRANSMITTER"},
        "FT": {"FT", "FLOW", "FLOWTRANSMITTER", "FLOWMETER"},
        "MCV": {"MCV", "MOTORCONTROLVALVE", "MOTORIZEDCONTROLVALVE", "MOTORIZEDVALVE"},
        "FSV&PCV": {"FSV", "PCV", "SHUTOFFVALVE", "PNEUMATICVALVE"},
        "SOV": {"SOV", "SOLENOID", "SOLENOIDVALVE"},
        "POS'R": {"POSR", "POSITIONER", "POSITIONERVALVE"},
        "LOAD CELL": {"LOADCELL", "LOADCELLRTD", "LOADCELLPWS", "WT"},
        "Analyser": {"ANALYSER", "ANALYZER", "GASANALYSER", "GASANALYZER"},
        "AIR COMPRESSOR": {"AIRCOMPRESSOR", "COMPRESSOR"},
        "Sheet1": {"GENERAL", "GENERALSPARES", "PLANTSPARES", "OTHERS"},
    }
    # Prefer explicit sheet token / family token over broad words.
    for sheet, vals in aliases.items():
        for a in vals:
            if _v14_norm(a) and _v14_norm(a) in qn:
                return sheet
    return None


def _v14_intent(q):
    ql = str(q).lower()
    status = None
    if any(x in ql for x in ("sufficient", "adequate", "enough stock", "in stock", "available stock", "available spares")):
        status = "SUFFICIENT STOCK"
    elif any(x in ql for x in ("zero stock", "no stock", "out of stock", "stock zero")):
        status = "ZERO STOCK"
    elif any(x in ql for x in ("below required", "shortage", "short", "indent", "to indent", "need to indent")):
        status = "BELOW REQUIRED"
    elif any(x in ql for x in ("not recorded", "unknown stock")):
        status = "STOCK NOT RECORDED"
    return status


def search_spares(query, limit=500):
    """V1.4 deterministic search: family/status/general filters before scoring."""
    rows = _v14_load_spares()
    if not rows:
        return []
    sheet = _v14_sheet_hint(query)
    status = _v14_intent(query)
    qn = _v14_norm(query)
    import re as _re
    re = _re
    tokens = [_v14_norm(x) for x in _re.findall(r"[A-Za-z0-9_-]+", str(query)) if _v14_norm(x) not in _STATUS_STOP]

    # Exact equipment/tag queries must win over broad family/status words.
    exact_tag = None
    query_tag_tokens = {_v14_norm(x) for x in re.findall(r"[A-Za-z0-9_-]+", str(query))}
    for r in rows:
        tag = _v14_norm(r.get("tag"))
        if tag and len(tag) >= 3 and tag in query_tag_tokens:
            exact_tag = tag
            break
    candidates = rows
    if exact_tag:
        candidates = [r for r in candidates if _v14_norm(r.get("tag")) == exact_tag]
        if status:
            candidates = [r for r in candidates if r["status"] == status]
        return candidates[:limit]

    # Explicit status/family queries must be deterministic, not fuzzy.
    if sheet:
        candidates = [r for r in candidates if r["sheet"] == sheet]
    if status:
        candidates = [r for r in candidates if r["status"] == status]

    # If a specific family/status query produced records, return them directly.
    if (sheet or status) and candidates:
        return candidates[:limit]

    scored = []
    for r in candidates:
        fields = " ".join([r.get("tag", ""), r.get("instrument", ""), r.get("item", ""), r.get("description", ""), r.get("specification", ""), r.get("location", ""), r.get("sheet", "")])
        fn = _v14_norm(fields)
        score = 0
        if qn and qn in fn:
            score += 80
        for t in tokens:
            if t and t in fn:
                score += 15
        tag_norm = _v14_norm(r.get("tag"))
        if tag_norm and any(_v14_norm(t) == tag_norm for t in tokens):
            score += 100
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], x[1]["sheet"], x[1]["row"]))
    return [r for _, r in scored[:limit]]


def answer_spare_query(query):
    rows = search_spares(query)
    # Explicit general/status/family queries should return a clear answer even when empty.
    explicit = bool(_v14_sheet_hint(query) or _v14_intent(query))
    if not rows and not explicit:
        return None
    if not rows:
        return {
            "answer": "ANVI found no verified critical spare records matching that filter. Source: critical spares in pci.xlsx.",
            "domain": "critical_spares", "evidence": "critical spares in pci.xlsx", "count": 0,
            "records": [], "read_only": True, "plc_write": False, "scada_control": False,
            "human_decision_required": True,
        }
    lines = [f"ANVI found {len(rows)} verified critical spare instrument record(s). Source: critical spares in pci.xlsx."]
    for r in rows:
        qty = r.get("qty_available")
        req = r.get("qty_required")
        indent = r.get("spare_to_indent")
        qty_text = f"Available: {qty}" if qty not in (None, "") else "Available: not recorded"
        req_text = f"Required: {req}" if req not in (None, "") else "Required: not recorded"
        ind_text = f"Spare to indent: {indent}" if indent not in (None, "") else "Spare to indent: not recorded"
        lines.append(f"{r.get('tag') or r.get('instrument') or r.get('item') or 'UNNAMED'} — {r.get('instrument') or r.get('item') or r.get('description') or 'Critical spare instrument'}; {qty_text}; {req_text}; Status: {r.get('status')}; {ind_text}; Sheet: {r.get('sheet')}; Row: {r.get('row')}.")
        if r.get("location"):
            lines.append(f"Location: {r['location']}")
        if r.get("specification"):
            lines.append(f"Specification: {r['specification']}")
    return {
        "answer": "\n".join(lines), "domain": "critical_spares", "evidence": "critical spares in pci.xlsx",
        "count": len(rows), "records": rows, "read_only": True, "plc_write": False,
        "scada_control": False, "human_decision_required": True,
    }


# ============================================================
# ANVIQO COMPATIBILITY API
# V1.4 — query_spares wrapper
# Preserves the existing V1.4 spare intelligence engine.
# ============================================================

def query_spares(question):
    """Compatibility wrapper for external tests/API callers."""
    return answer_spare_query(question)


# ================================================================
# ANVIQO CRITICAL SPARES V1.5
# CONVERSATIONAL SPARE MANAGEMENT
#
# Query -> Proposal -> Human Confirmation -> Existing Mutation
#
# SAFETY:
# PLC write       = FALSE
# SCADA control   = FALSE
# Human decision  = REQUIRED
#
# This layer intentionally does NOT duplicate or replace the
# existing inventory mutation/audit functions.
# ================================================================

import re as _v15_re
from datetime import datetime as _v15_datetime


def _v15_extract_quantity(question):
    q = str(question or "")
    patterns = [
        r'\b(\d+(?:\.\d+)?)\s*(?:nos?|number|numbers|pcs?|pieces?|qty|quantity)\b',
        r'\b(?:add|receive|received|increase|put)\s+(\d+(?:\.\d+)?)\b',
    ]

    for pattern in patterns:
        m = _v15_re.search(pattern, q, _v15_re.I)
        if m:
            value = float(m.group(1))
            return int(value) if value.is_integer() else value

    return None


def _v15_action(question):
    q = str(question or "").lower()

    if any(x in q for x in (
        "add spare", "add spares",
        "new spare", "new spares",
        "receive spare", "receive spares",
        "received spare", "received spares",
        "increase stock", "increase spare"
    )):
        return "ADD"

    if any(x in q for x in (
        "use spare", "used spare",
        "consume spare", "consumed spare",
        "issue spare", "issued spare",
        "remove spare", "remove spares"
    )):
        return "USE"

    if any(x in q for x in (
        "set stock", "update stock",
        "change stock", "adjust stock"
    )):
        return "ADJUST"

    return None


def _v15_extract_tag(question):
    q = str(question or "")

    # Strong instrument tag patterns:
    # PT-303 / PT303 / MCV-205 / FSV-501 etc.
    patterns = [
        r'\b([A-Z]{2,8}-?\d{2,5}(?:/[A-Z]{2,8}-?\d{2,5})*)\b'
    ]

    for pattern in patterns:
        m = _v15_re.search(pattern, q, _v15_re.I)
        if m:
            return m.group(1).upper()

    return None


def _v15_find_existing_mutation(action):
    """
    Locate an existing mutation function without assuming its name.
    Returns function name or None.
    """
    candidates = {
        "ADD": (
            "add_spare", "add_spares",
            "receive_spare", "receive_spares",
            "record_spare"
        ),
        "USE": (
            "use_spare", "use_spares",
            "consume_spare", "issue_spare",
            "remove_spare", "remove_spares"
        ),
        "ADJUST": (
            "adjust_spare", "adjust_stock",
            "update_spare", "update_stock"
        ),
    }

    for name in candidates.get(action, ()):
        fn = globals().get(name)
        if callable(fn):
            return name

    return None


def propose_spare_mutation(question):
    """
    Converts natural-language spare management into a proposal.

    NO INVENTORY CHANGE IS PERFORMED.

    The host/router must call confirm_spare_mutation()
    only after explicit human confirmation.
    """
    action = _v15_action(question)
    quantity = _v15_extract_quantity(question)
    tag = _v15_extract_tag(question)

    if not action:
        return {
            "ok": False,
            "type": "spare_management",
            "error": "No supported spare-management action detected.",
            "human_decision_required": True,
        }

    if quantity is None or quantity <= 0:
        return {
            "ok": False,
            "type": "spare_management",
            "action": action,
            "tag": tag,
            "error": "A positive quantity is required.",
            "human_decision_required": True,
        }

    if not tag:
        return {
            "ok": False,
            "type": "spare_management",
            "action": action,
            "quantity": quantity,
            "error": "A spare tag/item identifier is required.",
            "human_decision_required": True,
        }

    mutation_function = _v15_find_existing_mutation(action)

    return {
        "ok": True,
        "type": "spare_management_proposal",
        "action": action,
        "tag": tag,
        "quantity": quantity,
        "existing_mutation_function": mutation_function,
        "confirmed": False,
        "executed": False,
        "human_decision_required": True,
        "plc_write": False,
        "scada_control": False,
        "message": (
            f"PROPOSED ACTION: {action} {quantity} spare(s) "
            f"for {tag}. No inventory has been changed. "
            f"Explicit human confirmation is required."
        ),
    }


def confirm_spare_mutation(proposal, confirmed=False):
    """
    Execute an existing mutation function ONLY after explicit
    confirmation.

    If the existing mutation API cannot be safely identified,
    nothing is changed.
    """
    if not isinstance(proposal, dict):
        return {
            "ok": False,
            "error": "Invalid spare-management proposal.",
            "executed": False,
            "human_decision_required": True,
        }

    if not confirmed:
        return {
            **proposal,
            "confirmed": False,
            "executed": False,
            "message": "Confirmation not received. No inventory changed.",
        }

    fn_name = proposal.get("existing_mutation_function")

    if not fn_name:
        return {
            **proposal,
            "confirmed": True,
            "executed": False,
            "error": (
                "No compatible existing mutation function was safely "
                "identified. No inventory changed."
            ),
            "human_decision_required": True,
        }

    fn = globals().get(fn_name)

    if not callable(fn):
        return {
            **proposal,
            "confirmed": True,
            "executed": False,
            "error": "Mutation function is unavailable. No inventory changed.",
            "human_decision_required": True,
        }

    # Do not guess an unknown function signature.
    # V1.5 intentionally stops here until the existing function's
    # contract is explicitly known.
    return {
        **proposal,
        "confirmed": True,
        "executed": False,
        "error": (
            f"Existing mutation function '{fn_name}' detected, "
            "but V1.5 will not guess its arguments. "
            "Use the existing mutation API through its defined contract."
        ),
        "human_decision_required": True,
        "safe_execution": False,
    }


def answer_spare_management(question):
    """
    Conversational entry point.

    Query questions continue through answer_spare_query().
    Mutation requests become confirmation-required proposals.
    """
    action = _v15_action(question)

    if action:
        return propose_spare_mutation(question)

    return answer_spare_query(question)



# ================================================================
# ANVIQO CRITICAL SPARES V1.6
# SAFE CONVERSATIONAL INVENTORY MUTATION
# ================================================================

import re as _v16_re
import openpyxl as _v16_openpyxl
from datetime import datetime as _v16_datetime
from pathlib import Path as _v16_Path

_V16_XLSX = _v16_Path(__file__).resolve().parent / \
    "database" / "spares" / "critical_spares.xlsx"

_V16_AUDIT = _V16_XLSX.parent / "spare_inventory_audit.log"


def _v16_action(q):
    q = str(q or "").lower()

    # ADD / RECEIVE
    if any(x in q for x in (
        "add", "receive", "received",
        "increase", "put"
    )) and "spare" in q:
        return "ADD"

    # USE / CONSUME / ISSUE / REMOVE
    if any(x in q for x in (
        "use", "used", "consume", "consumed",
        "issue", "issued", "remove", "decrease"
    )) and "spare" in q:
        return "USE"

    return None

def _v16_quantity(q):
    q = str(q or "")

    patterns = [
        r'\b(\d+)\s*(?:nos?|numbers?|pcs?|pieces?|qty|quantity)\b',
        r'\b(?:add|receive|received|increase|put|use|used|consume|issue|issued|remove)\s+(\d+)\b'
    ]

    for pattern in patterns:
        m = _v16_re.search(pattern, q, _v16_re.I)
        if m:
            n = int(m.group(1))
            if n > 0:
                return n

    return None


def _v16_identifier(q):
    q = str(q or "").strip()
    upper = q.upper()

    # Exact equipment tags: PT-303, MCV-205, FSV-501 etc.
    words = upper.split()

    for word in words:
        clean = word.strip(".,;:()[]{}")
        if "-" in clean:
            left, right = clean.split("-", 1)
            if left.isalpha() and right.isdigit():
                return clean

    # Exact PCI inventory identifiers.
    # Example:
    # PCI_BOKE 4M310-08
    # PCI_BOKE 4V310-10
    # PCI_ZMF-Y-76S
    marker = "PCI_"
    pos = upper.find(marker)

    if pos >= 0:
        value = upper[pos:]

        # Remove command-ending words.
        for ending in (" SPARES", " SPARE", " PIECES", " PCS"):
            idx = value.find(ending)
            if idx >= 0:
                value = value[:idx]

        value = " ".join(value.split()).strip(".,;:()[]{}")

        if value:
            return value

    # Family-only identifiers are allowed for SEARCH,
    # but mutation must reject ambiguous families.
    for family in (
        "SOV", "FSV", "PCV", "FCV", "MCV",
        "PT", "LT", "FT", "RTD"
    ):
        if family in upper:
            return family

    return None

def _v16_find(identifier):
    rows = _v14_load_spares()
    ident = str(identifier).upper().replace("-", "")

    matches = []

    for r in rows:
        tag = str(r.get("tag") or "").upper().replace("-", "")
        instrument = str(r.get("instrument") or "").upper().replace("-", "")

        if ident == tag or ident == instrument:
            matches.append(r)

    return matches


def execute_spare_mutation(question, confirmed=False):
    """
    V1.6.3 controlled conversational inventory mutation.

    Natural language -> validated action/quantity/identifier
    -> exact inventory match -> safety gate -> Excel mutation
    -> verification -> audit.

    PLC/SCADA are never touched.
    """

    action = _v16_action(question)
    quantity = _v16_quantity(question)
    identifier = _v16_identifier(question)

    base = {
        "ok": False,
        "executed": False,
        "human_decision_required": True,
        "plc_write": False,
        "scada_control": False,
    }

    if not action:
        return {
            **base,
            "error": "No supported spare action detected."
        }

    if quantity is None or quantity <= 0:
        return {
            **base,
            "action": action,
            "error": "A positive quantity is required."
        }

    if not identifier:
        return {
            **base,
            "action": action,
            "quantity": quantity,
            "error": "No spare tag/item identifier found."
        }

    matches = _v16_find(identifier)

    if not matches:
        # Category-only identifier such as SOV, PT, MCV, FT, etc.
        # Never mutate a category because it may contain multiple records.
        category_matches = []
        ident_norm = str(identifier).upper().replace("-", "").strip()

        for r in _v14_load_spares():
            tag = str(r.get("tag") or "").upper().replace("-", "").strip()
            instrument = str(r.get("instrument") or "").upper().strip()
            item = str(r.get("item") or "").upper().strip()

            if (
                tag.startswith(ident_norm) or
                instrument.startswith(ident_norm) or
                item.startswith(ident_norm)
            ):
                category_matches.append(r)

        if category_matches:
            lines = [
                f"'{identifier}' matches {len(category_matches)} spare records. "
                "Exact item/tag required. No inventory changed."
            ]

            for r in category_matches[:20]:
                name = (
                    r.get("tag") or
                    r.get("instrument") or
                    r.get("item") or
                    "UNNAMED"
                )
                lines.append(
                    f"- {name} | Sheet: {r.get('sheet')} | "
                    f"Row: {r.get('row')} | "
                    f"Available: {r.get('qty_available')}"
                )

            return {
                **base,
                "action": action,
                "quantity": quantity,
                "identifier": identifier,
                "ambiguous": True,
                "matches": len(category_matches),
                "error": "\n".join(lines)
            }

        return {
            **base,
            "action": action,
            "quantity": quantity,
            "identifier": identifier,
            "error": f"No spare tag/item/category found for {identifier}."
        }

    # Category-only commands are ambiguous for mutation.
    if len(matches) > 1:
        return {
            **base,
            "action": action,
            "quantity": quantity,
            "identifier": identifier,
            "error": (
                f"Ambiguous spare identifier '{identifier}'. "
                f"{len(matches)} records found. Use an exact tag/item identifier."
            )
        }

    record = matches[0]

    tag = record.get("tag") or record.get("instrument") or identifier
    sheet = record.get("sheet")
    row = record.get("row")
    before = float(record.get("qty_available") or 0)

    if action == "USE" and quantity > before:
        return {
            **base,
            "action": action,
            "tag": tag,
            "quantity": quantity,
            "before": before,
            "error": (
                f"Insufficient stock for {tag}. "
                f"Available: {int(before) if before.is_integer() else before}; "
                f"Requested: {quantity}. No inventory changed."
            )
        }

    if not confirmed:
        return {
            **base,
            "message": (
                f"Confirmation required for {action} {quantity} "
                f"spare(s) of {tag}. No inventory changed."
            )
        }

    # Locate the exact available-stock cell.
    import openpyxl

    wb = openpyxl.load_workbook(str(_V16_XLSX))
    ws = wb[sheet]

    available_col = None

    # Prefer the existing parsed column if available.
    for col in range(1, ws.max_column + 1):
        header = str(ws.cell(1, col).value or "").strip().lower()
        if header in (
            "qty avbl", "qty available", "available",
            "available qty", "qty_avbl"
        ):
            available_col = col
            break

    if available_col is None:
        # Known V1.x workbook layouts use the parsed raw column.
        raw = record.get("raw") or {}
        for key in raw:
            try:
                col = int(key) + 1
            except Exception:
                continue
            value = ws.cell(1, col).value
            if str(value or "").strip().lower() in (
                "qty avbl", "qty available", "available"
            ):
                available_col = col
                break

    if available_col is None:
        wb.close()
        return {
            **base,
            "action": action,
            "tag": tag,
            "quantity": quantity,
            "error": "Available-stock column could not be safely identified."
        }

    current = float(ws.cell(row, available_col).value or 0)

    # Re-check immediately before write.
    if action == "USE" and quantity > current:
        wb.close()
        return {
            **base,
            "action": action,
            "tag": tag,
            "quantity": quantity,
            "before": current,
            "error": (
                f"Insufficient stock for {tag}. "
                f"Available: {int(current) if current.is_integer() else current}; "
                f"Requested: {quantity}. No inventory changed."
            )
        }

    if action == "ADD":
        after = current + quantity
    elif action == "USE":
        after = current - quantity
    else:
        wb.close()
        return {
            **base,
            "action": action,
            "tag": tag,
            "quantity": quantity,
            "error": "ADJUST requires an explicit target stock value."
        }

    if after < 0:
        wb.close()
        return {
            **base,
            "action": action,
            "tag": tag,
            "quantity": quantity,
            "before": current,
            "error": "Safety block: inventory cannot become negative."
        }

    ws.cell(row, available_col).value = int(after) if after.is_integer() else after
    wb.save(str(_V16_XLSX))
    wb.close()

    # Independent verification after save.
    verify_wb = openpyxl.load_workbook(str(_V16_XLSX), data_only=False, read_only=True)
    verify_ws = verify_wb[sheet]
    verified_value = float(verify_ws.cell(row, available_col).value or 0)
    verify_wb.close()

    verified = abs(verified_value - after) < 1e-9

    if not verified:
        return {
            **base,
            "action": action,
            "tag": tag,
            "quantity": quantity,
            "before": current,
            "after": verified_value,
            "verified": False,
            "error": "Excel verification failed after mutation."
        }

    # Audit log.
    _V16_AUDIT.parent.mkdir(parents=True, exist_ok=True)

    timestamp = _v16_datetime.now().isoformat(timespec="seconds")
    with open(_V16_AUDIT, "a", encoding="utf-8") as f:
        f.write(
            f"{timestamp} | {action} | {tag} | "
            f"Sheet={sheet} | Row={row} | "
            f"AvailableColumn={available_col} | "
            f"Before={current:g} | Quantity={quantity:g} | "
            f"After={after:g} | VERIFIED=YES\n"
        )

    return {
        "ok": True,
        "executed": True,
        "action": action,
        "tag": tag,
        "quantity": quantity,
        "before": current,
        "after": after,
        "sheet": sheet,
        "row": row,
        "available_column": available_col,
        "verified": True,
        "audit_log": str(_V16_AUDIT),
        "plc_write": False,
        "scada_control": False,
        "human_decision_required": True,
        "answer": (
            "ANVIQO inventory updated successfully.\n"
            f"{tag}: {current:g} -> {after:g}\n"
            f"Action: {action}; Quantity: {quantity:g}\n"
            f"Sheet: {sheet}; Row: {row}\n"
            f"Available column: {available_col}\n"
            "Excel verified: YES\n"
            "PLC write: FALSE\n"
            "SCADA control: FALSE"
        )
    }

def answer_spare_management_v16(question, confirmed=False):

    if _v16_action(question):
        return execute_spare_mutation(
            question,
            confirmed=confirmed
        )

    return answer_spare_query(question)

