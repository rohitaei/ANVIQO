#!/usr/bin/env python3
"""ANVIQO Critical Spare Intelligence V1.4 query patch.

Safe patch: backs up pci_spares.py, then APPENDS query-layer overrides only.
It does not replace existing add/used/received/remove/audit logic and does not
write to PLC/SCADA.
"""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path.cwd()
MODULE = ROOT / "pci_spares.py"
if not MODULE.exists():
    raise SystemExit("STOP: pci_spares.py not found. No file was modified.")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = MODULE.with_name(f"pci_spares_BEFORE_V1_4_{stamp}.py")
shutil.copy2(MODULE, backup)

patch = r'''

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
'''

text = MODULE.read_text(encoding="utf-8")
text += patch
MODULE.write_text(text, encoding="utf-8")
print("ANVIQO CRITICAL SPARES V1.4 PATCH INSTALLED")
print("Module :", MODULE)
print("Backup :", backup)
print("Safety : read-only / PLC write FALSE / SCADA control FALSE")
print("Preserved: existing mutation + audit functions")
