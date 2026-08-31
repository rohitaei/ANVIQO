"""
ANVIQO V1.2 DIRECT EXCEL SPARE ENGINE

Authoritative current inventory:
    database/spares/critical_spares.xlsx

Rules:
- Explicit ADD/RECEIVED modifies Excel directly.
- Explicit USED/REMOVE modifies Excel directly.
- Quantity can never become negative.
- Transaction JSON remains audit/history only.
- No PLC write.
- No SCADA control.
"""

from pathlib import Path
from datetime import datetime, timezone
from openpyxl import load_workbook
import re
import json

ROOT = Path(__file__).resolve().parent
XLSX = ROOT / "database" / "spares" / "critical_spares.xlsx"
AUDIT = ROOT / "database" / "spares" / "critical_spare_transactions.json"


def _norm(v):
    return re.sub(r"[^a-z0-9]+", " ", str(v or "").lower()).strip()


def _number(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def _find_tag(ws, tag):
    target = _norm(tag)

    for row in ws.iter_rows():
        for cell in row:
            if _norm(cell.value) == target:
                return cell.row

    # fallback substring match
    for row in ws.iter_rows():
        for cell in row:
            value = _norm(cell.value)
            if target and target in value:
                return cell.row

    return None


def _find_header(ws, names):
    wanted = {_norm(x) for x in names}

    for cell in ws[1]:
        if _norm(cell.value) in wanted:
            return cell.column

    return None


def _load_audit():
    if not AUDIT.exists():
        return {"transactions": []}

    try:
        return json.loads(AUDIT.read_text(encoding="utf-8"))
    except Exception:
        return {"transactions": []}


def _save_audit(data):
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    tmp = AUDIT.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    tmp.replace(AUDIT)


def _audit(action, tag, quantity, before, after):
    data = _load_audit()

    txn_id = (
        "SPARE-DIRECT-"
        + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:-3]
    )

    data.setdefault("transactions", []).append({
        "transaction_id": txn_id,
        "action": action,
        "tag": tag,
        "quantity": quantity,
        "quantity_before": before,
        "quantity_after": after,
        "status": "APPLIED",
        "applied_directly_to_excel": True,
        "source": "critical_spares.xlsx",
        "plc_write": False,
        "scada_control": False,
        "human_confirmation_required": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat()
    })

    _save_audit(data)

    return txn_id


def update_spare(tag, quantity, action):
    tag = str(tag).strip().upper()
    quantity = float(quantity)

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    action = action.upper().strip()

    if action not in ("ADD", "REMOVE"):
        raise ValueError("Action must be ADD or REMOVE.")

    if not XLSX.exists():
        raise FileNotFoundError(f"Spare workbook not found: {XLSX}")

    # Keep formulas intact while updating the workbook.
    wb = load_workbook(XLSX, data_only=False)

    found = None

    for ws in wb.worksheets:
        row = _find_tag(ws, tag)
        if row is not None:
            qty_col = _find_header(
                ws,
                ["Qty avbl", "Qty available", "Qty Avbl"]
            )

            if qty_col is not None:
                found = (ws, row, qty_col)
                break

    if found is None:
        raise ValueError(
            f"Spare tag {tag} was not found in critical_spares.xlsx."
        )

    ws, row, qty_col = found

    old_qty = _number(ws.cell(row, qty_col).value)

    if action == "ADD":
        new_qty = old_qty + quantity
    else:
        if quantity > old_qty:
            raise ValueError(
                f"Cannot remove {quantity:g} {tag}. "
                f"Only {old_qty:g} available."
            )
        new_qty = old_qty - quantity

    # Preserve integer quantities as integers.
    if float(new_qty).is_integer():
        new_value = int(new_qty)
    else:
        new_value = new_qty

    ws.cell(row, qty_col).value = new_value

    # Save workbook atomically.
    tmp = XLSX.with_suffix(".v120.tmp.xlsx")
    wb.save(tmp)
    tmp.replace(XLSX)

    txn_id = _audit(
        action,
        tag,
        quantity,
        old_qty,
        new_qty
    )

    return {
        "tag": tag,
        "action": action,
        "quantity": quantity,
        "before": old_qty,
        "after": new_qty,
        "transaction_id": txn_id,
        "file": str(XLSX)
    }


def add_spare(tag, quantity):
    return update_spare(tag, quantity, "ADD")


def remove_spare(tag, quantity):
    return update_spare(tag, quantity, "REMOVE")


def get_spare_quantity(tag):
    tag = str(tag).strip().upper()

    wb = load_workbook(XLSX, data_only=False)

    for ws in wb.worksheets:
        row = _find_tag(ws, tag)

        if row is None:
            continue

        qty_col = _find_header(
            ws,
            ["Qty avbl", "Qty available", "Qty Avbl"]
        )

        if qty_col is None:
            continue

        return _number(ws.cell(row, qty_col).value)

    raise ValueError(
        f"Spare tag {tag} was not found in critical_spares.xlsx."
    )


if __name__ == "__main__":
    print("ANVIQO V1.2 DIRECT EXCEL ENGINE")
    print("PT-303 quantity:", get_spare_quantity("PT-303"))
