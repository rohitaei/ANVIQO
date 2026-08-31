"""
ANVIQO CRITICAL SPARE TRANSACTION ENGINE V1

Purpose:
    Controlled inventory additions/removals.

Safety:
    - Does NOT modify critical_spares.xlsx.
    - Does NOT access PLC.
    - Does NOT access SCADA.
    - Every write requires explicit confirmation.
    - Every approved transaction is permanently logged.

The Excel workbook remains the original evidence source.
ANVIQO adjustments are maintained as a separate transaction overlay.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
import uuid


ROOT = Path(__file__).resolve().parent

TRANSACTION_FILE = (
    ROOT
    / "database"
    / "spares"
    / "critical_spare_transactions.json"
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _ensure_store():
    TRANSACTION_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not TRANSACTION_FILE.exists():
        TRANSACTION_FILE.write_text(
            json.dumps(
                {
                    "version": "SPARE-TXN-1.0",
                    "transactions": []
                },
                indent=2
            ),
            encoding="utf-8"
        )


def load_transactions():
    _ensure_store()

    try:
        data = json.loads(
            TRANSACTION_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        return []

    return data.get("transactions", [])


def _save_transactions(transactions):
    _ensure_store()

    payload = {
        "version": "SPARE-TXN-1.0",
        "transactions": transactions
    }

    tmp = TRANSACTION_FILE.with_suffix(".tmp")

    tmp.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    tmp.replace(TRANSACTION_FILE)


def create_transaction(
    tag,
    quantity,
    action="ADD",
    requested_by="ANVI",
    reason=""
):
    """
    Create a PENDING transaction.

    No inventory is changed until confirm_transaction()
    is called.
    """

    action = str(action).upper().strip()
    tag = str(tag or "").strip()

    try:
        quantity = float(quantity)
    except Exception:
        raise ValueError("Quantity must be numeric.")

    if not tag:
        raise ValueError("Spare tag is required.")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    if action not in {"ADD", "REMOVE"}:
        raise ValueError("Action must be ADD or REMOVE.")

    txn = {
        "transaction_id": (
            "SPARE-TXN-"
            + datetime.now().strftime("%Y%m%d%H%M%S")
            + "-"
            + uuid.uuid4().hex[:8].upper()
        ),
        "timestamp_utc": _utc_now(),
        "tag": tag,
        "quantity": quantity,
        "action": action,
        "status": "PENDING",
        "requested_by": requested_by,
        "reason": reason,
    }

    transactions = load_transactions()
    transactions.append(txn)
    _save_transactions(transactions)

    return txn


def get_transaction(transaction_id):
    for txn in load_transactions():
        if txn.get("transaction_id") == transaction_id:
            return txn

    return None



def get_source_quantity(tag):
    """
    Return authoritative source quantity for an instrument spare tag.

    READ-ONLY:
    - Does not modify critical_spares.xlsx.
    - Uses pci_spares.load_spares().
    - Sums matching source records for the normalized tag.
    """

    target = str(tag or "").strip().upper()

    if not target:
        return 0.0

    from pci_spares import load_spares

    total = 0.0

    for row in load_spares():
        row_tag = str(
            row.get("tag")
            or row.get("instrument_tag")
            or row.get("name")
            or ""
        ).strip().upper()

        if row_tag != target:
            continue

        value = (
            row.get("qty_available")
            if row.get("qty_available") is not None
            else row.get("qty")
        )

        try:
            total += float(value)
        except (TypeError, ValueError):
            continue

    return total


def confirm_transaction(transaction_id, confirmed_by="USER"):
    """
    Approve a pending transaction.

    This is the ONLY operation that changes transaction state
    from PENDING to CONFIRMED.
    """

    transactions = load_transactions()

    found = None

    for txn in transactions:
        if txn.get("transaction_id") == transaction_id:
            found = txn
            break

    if found is None:
        raise ValueError("Transaction not found.")

    if found.get("status") != "PENDING":
        raise ValueError(
            f"Transaction is already {found.get('status')}."
        )

    # --------------------------------------------------------
    # NEGATIVE INVENTORY PROTECTION
    #
    # Only REMOVE transactions require stock validation.
    # Existing CONFIRMED transactions are already represented
    # by effective_delta().
    #
    # Source quantity comes from pci_spares.load_spares()
    # and is READ-ONLY.
    # --------------------------------------------------------
    if found.get("action") == "REMOVE":
        tag = str(found.get("tag", "")).strip().upper()
        quantity = float(found.get("quantity", 0))

        source_qty = get_source_quantity(tag)
        confirmed_delta = effective_delta(tag)

        effective_before = source_qty + confirmed_delta
        effective_after = effective_before - quantity

        if effective_after < 0:
            raise ValueError(
                "Negative inventory protection: "
                f"cannot remove {quantity:g} of {tag}. "
                f"Effective inventory before confirmation: "
                f"{effective_before:g}."
            )

    found["status"] = "CONFIRMED"
    found["confirmed_at_utc"] = _utc_now()
    found["confirmed_by"] = confirmed_by

    _save_transactions(transactions)

    return found


def cancel_transaction(transaction_id, cancelled_by="USER"):
    """
    Cancel a pending transaction.
    """

    transactions = load_transactions()

    found = None

    for txn in transactions:
        if txn.get("transaction_id") == transaction_id:
            found = txn
            break

    if found is None:
        raise ValueError("Transaction not found.")

    if found.get("status") != "PENDING":
        raise ValueError(
            f"Transaction is already {found.get('status')}."
        )

    found["status"] = "CANCELLED"
    found["cancelled_at_utc"] = _utc_now()
    found["cancelled_by"] = cancelled_by

    _save_transactions(transactions)

    return found


def effective_delta(tag):
    """
    Return the net quantity adjustment for a tag.

    Only CONFIRMED transactions affect inventory.
    """

    target = str(tag or "").strip().upper()

    delta = 0.0

    for txn in load_transactions():

        if txn.get("status") != "CONFIRMED":
            continue

        if str(txn.get("tag", "")).strip().upper() != target:
            continue

        qty = float(txn.get("quantity", 0))

        if txn.get("action") == "ADD":
            delta += qty

        elif txn.get("action") == "REMOVE":
            delta -= qty

    return delta


def pending_transactions():
    return [
        txn
        for txn in load_transactions()
        if txn.get("status") == "PENDING"
    ]


def confirmed_transactions():
    return [
        txn
        for txn in load_transactions()
        if txn.get("status") == "CONFIRMED"
    ]


def transaction_status():
    transactions = load_transactions()

    return {
        "file": str(TRANSACTION_FILE),
        "total": len(transactions),
        "pending": sum(
            1 for x in transactions
            if x.get("status") == "PENDING"
        ),
        "confirmed": sum(
            1 for x in transactions
            if x.get("status") == "CONFIRMED"
        ),
        "cancelled": sum(
            1 for x in transactions
            if x.get("status") == "CANCELLED"
        ),
        "read_only_source_preserved": True,
        "plc_write": False,
        "scada_control": False,
        "human_confirmation_required": True,
    }
