"""Plant-scoped critical-spares query path.

Only reads spare records imported into the authenticated plant's own
anviqo_plant_knowledge rows. It never reads the repository/global workbook.
"""
from __future__ import annotations

import re
from typing import Any

SAFETY = {
    "tenant_scoped": True,
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
}


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _pick(metadata: dict, *aliases: str):
    if not isinstance(metadata, dict):
        return None
    wanted = {_key(x) for x in aliases}
    for key, value in metadata.items():
        if _key(key) in wanted and value not in (None, ""):
            return value
    return None


def _number(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group(0)) if match else None


def _stock_status(available, required=None, reorder=None):
    if available is None:
        return "STOCK NOT RECORDED"
    if available <= 0:
        return "ZERO STOCK"
    if required is not None and available < required:
        return "BELOW REQUIRED"
    if reorder is not None and available <= reorder:
        return "LOW STOCK"
    return "SUFFICIENT STOCK"


def is_spare_question(question: str) -> bool:
    low = str(question or "").lower()
    return any(x in low for x in (
        "spare", "spares", "inventory", "stock", "indent"
    ))


def is_low_stock_question(question: str) -> bool:
    low = str(question or "").lower()
    return any(x in low for x in (
        "low stock", "low-stock", "low inventory", "below minimum",
        "minimum stock", "reorder", "shortage", "below required",
        "short stock", "zero stock", "out of stock", "no stock",
        "to indent", "need to indent",
    ))


def _load(plant_id: str, organization_id: str):
    import anvi_tenant_store as store

    if not plant_id or not organization_id:
        raise PermissionError("An authenticated selected plant is required.")
    p = store._placeholder()
    sql = (
        "SELECT k.external_id,k.name,k.area,k.service,k.tag,k.source,"
        "k.metadata,d.filename "
        "FROM anviqo_plant_knowledge k "
        "LEFT JOIN anviqo_plant_documents d ON d.document_id=k.document_id "
        f"WHERE k.plant_id={p} AND k.organization_id={p} "
        "AND UPPER(k.record_type) IN ('CRITICAL_SPARE','SPARE','SPARE_INVENTORY') "
        "ORDER BY k.area,k.tag,k.external_id LIMIT 2000"
    )
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(sql, (plant_id, organization_id))
        return cur.fetchall()


def _value(row, index, name):
    if isinstance(row, dict):
        return row.get(name)
    if hasattr(row, "keys"):
        try:
            return row[name]
        except Exception:
            pass
    return row[index]


def answer(question: str, plant_id: str, organization_id: str):
    if not is_spare_question(question):
        return None

    try:
        rows = _load(plant_id, organization_id)
    except Exception as exc:
        return {
            "answer": "ANVI could not read the selected plant's spare inventory. No other plant's data was used. Please retry after the inventory store is available.",
            "domain": "critical_spares",
            "evidence_status": "QUERY_ERROR",
            "error_type": type(exc).__name__,
            "plant_id": plant_id,
            **SAFETY,
        }

    if not rows:
        return {
            "answer": (
                "The selected plant has no critical-spare inventory onboarded yet. "
                "Upload this plant's critical_spares.xlsx (or its approved spare register) "
                "under Plant Onboarding Documents, then run Import/Index. "
                "The spare query is restricted to this selected plant; no other plant's "
                "inventory or shared workbook was used."
            ),
            "domain": "critical_spares",
            "evidence_status": "SPARE_INVENTORY_NOT_ONBOARDED",
            "count": 0,
            "plant_id": plant_id,
            **SAFETY,
        }

    low_stock_only = is_low_stock_question(question)
    query_tokens = {
        _key(x) for x in re.findall(r"[A-Za-z]{1,10}[-_ ]?\d{1,6}", str(question or ""))
    }
    records = []
    for row in rows:
        external_id = str(_value(row, 0, "external_id") or "")
        name = str(_value(row, 1, "name") or "")
        area = str(_value(row, 2, "area") or "")
        service = str(_value(row, 3, "service") or "")
        raw_tag = str(_value(row, 4, "tag") or "").strip()
        source = str(_value(row, 5, "source") or "")
        metadata = _value(row, 6, "metadata") or {}
        filename = str(_value(row, 7, "filename") or source or "plant spare register")
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        # A synthetic external_id is a database key, not an equipment tag.
        # Never display placeholders such as NA or a generated sheet-row key
        # as if they were verified instrument identifiers.
        missing_tags = {"", "NA", "N/A", "NONE", "NULL", "NOT AVAILABLE", "UNKNOWN", "-"}
        if raw_tag.upper() not in missing_tags:
            display_tag = raw_tag
        else:
            sheet_name = str(_pick(metadata, "sheet_name", "worksheet", "sheet") or "").strip()
            workbook_row = _pick(metadata, "workbook_row", "excel_row", "row_number")
            if sheet_name and workbook_row not in (None, ""):
                display_tag = f"Tag not recorded (workbook row {sheet_name} #{workbook_row})"
            else:
                display_tag = "Tag not recorded"

        available = _number(_pick(
            metadata, "qty_available", "qty_avbl", "qty available",
            "quantity available", "available", "stock available",
            "qty in hand", "balance stock",
        ))
        required = _number(_pick(
            metadata, "qty_required", "qty_req", "qty required",
            "required quantity", "minimum quantity", "min qty",
            "required", "qty requirement",
        ))
        reorder = _number(_pick(
            metadata, "reorder_level", "reorder qty", "minimum stock",
            "min stock", "reorder point",
        ))
        status = _stock_status(available, required, reorder)

        if query_tokens and not any(
            token in _key(" ".join((tag, external_id, name, service)))
            for token in query_tokens
        ):
            continue
        if low_stock_only and status not in {
            "ZERO STOCK", "BELOW REQUIRED", "LOW STOCK"
        }:
            continue

        records.append({
            "tag": display_tag,
            "name": name or service,
            "area": area,
            "available": available,
            "required": required,
            "reorder_level": reorder,
            "status": status,
            "source": filename,
        })

    if not records and low_stock_only:
        answer_text = (
            f"Checked {len(rows)} critical-spare record(s) onboarded to the selected plant. "
            "No low-stock, below-required, or zero-stock records were found in that evidence."
        )
    elif not records:
        answer_text = (
            "No matching critical-spare records were found in the selected plant's onboarded inventory."
        )
    else:
        lines = [
            f"ANVI found {len(records)} selected-plant critical spare record(s)"
            + (" requiring stock attention." if low_stock_only else ".")
        ]
        for item in records[:100]:
            av = "not recorded" if item["available"] is None else f"{item['available']:g}"
            req = "not recorded" if item["required"] is None else f"{item['required']:g}"
            lines.append(
                f"{item['tag']} — {item['name'] or 'Critical spare'}; "
                f"Area: {item['area'] or 'not recorded'}; Available: {av}; "
                f"Required: {req}; Status: {item['status']}; Source: {item['source']}."
            )
        answer_text = "\n".join(lines)

    return {
        "answer": answer_text,
        "domain": "critical_spares",
        "evidence_status": "EVIDENCE_AVAILABLE" if records else "NO_MATCHING_SPARES",
        "count": len(records),
        "records": records,
        "plant_id": plant_id,
        **SAFETY,
    }
