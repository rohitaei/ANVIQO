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

    # Spare sheets can have a title row before the real table header.
    for row_no in range(1, min(ws.max_row, 10) + 1):
        for cell in ws[row_no]:
            if _norm(cell.value) in wanted:
                return cell.column

    return None




def _find_header_row(ws):
    """Locate the actual spare-table header row."""
    wanted = {
        "tag no", "tag", "description", "instrument",
        "qty avbl", "qty available", "qty", "qty req",
        "required", "location", "installation site", "instalation site",
    }
    best_row = 1
    best_score = -1
    for row_no in range(1, min(ws.max_row, 10) + 1):
        score = 0
        for cell in ws[row_no]:
            value = _norm(cell.value)
            if value in {_norm(x) for x in wanted}:
                score += 2
            elif any(_norm(x) in value for x in wanted):
                score += 1
        if score > best_score:
            best_score = score
            best_row = row_no
    return best_row


def _normalize_quantity_merges(wb):
    """
    One equipment/tag must own one independent Qty Available cell.

    Older spare workbooks may vertically merge Qty Available across several
    equipment rows. That is incompatible with direct inventory mutation:
    changing one tag would change another tag. For every unambiguous merged
    quantity block, copy the existing owner quantity into each tagged row and
    then unmerge the block. No new quantity is invented; the pre-existing
    workbook quantity is preserved as the starting value for each equipment.
    """
    changed = False
    for ws in wb.worksheets:
        header_row = _find_header_row(ws)
        qty_col = _find_header(
            ws, ["Qty avbl", "Qty available", "Qty Avbl", "Available", "Qty"]
        )
        if qty_col is None:
            continue

        tag_col = _find_header(ws, ["Tag No", "Tag", "Tag No."])
        if tag_col is None:
            continue

        for merged_range in list(ws.merged_cells.ranges):
            if not (merged_range.min_col <= qty_col <= merged_range.max_col):
                continue
            if merged_range.min_col != merged_range.max_col:
                continue
            if merged_range.max_row <= header_row:
                continue

            owner_value = ws.cell(
                merged_range.min_row, merged_range.min_col
            ).value

            tagged_rows = []
            for rr in range(
                max(header_row + 1, merged_range.min_row),
                merged_range.max_row + 1
            ):
                tag_value = _norm(ws.cell(rr, tag_col).value)
                if tag_value:
                    tagged_rows.append(rr)

            # Only normalize a block when every equipment row in it has an
            # identifiable tag. This prevents touching decorative merges.
            if not tagged_rows:
                continue
            if len(tagged_rows) != (
                merged_range.max_row - max(header_row + 1, merged_range.min_row) + 1
            ):
                continue

            ws.unmerge_cells(str(merged_range))
            for rr in tagged_rows:
                ws.cell(rr, qty_col).value = owner_value
            changed = True

    return changed


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


def ensure_independent_spare_inventory():
    """
    One-time/idempotent migration for the authoritative spare workbook.

    Every equipment/tag gets its own Qty Available cell. Legacy vertical
    quantity merges are expanded using the existing owner value, then the
    merged range is removed. No quantity is invented and no PLC/SCADA action
    is involved.
    """
    if not XLSX.exists():
        return {"changed": False, "file": str(XLSX)}

    wb = load_workbook(XLSX, data_only=False)
    changed = _normalize_quantity_merges(wb)

    if changed:
        tmp = XLSX.with_suffix(".independent.tmp.xlsx")
        wb.save(tmp)
        wb.close()
        tmp.replace(XLSX)
    else:
        wb.close()

    return {"changed": changed, "file": str(XLSX)}


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
    normalized = _normalize_quantity_merges(wb)
    if normalized:
        # Persist the one-cell-per-equipment migration before applying the
        # requested transaction.
        wb.save(XLSX)
        wb.close()
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
    normalized = _normalize_quantity_merges(wb)
    if normalized:
        wb.save(XLSX)
        wb.close()
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

        value = _number(ws.cell(row, qty_col).value)
        wb.close()
        return value

    wb.close()
    raise ValueError(
        f"Spare tag {tag} was not found in critical_spares.xlsx."
    )


if __name__ == "__main__":
    print("ANVIQO V1.2 DIRECT EXCEL ENGINE")
    print("PT-303 quantity:", get_spare_quantity("PT-303"))
