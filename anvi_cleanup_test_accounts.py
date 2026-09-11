"""One-time cleanup for tenant test accounts.

Deletes tenant user accounts except the configured original ANVIQO admin.
Does not touch PCI/V5 files, plant data, inventory, or intelligence modules.
Enabled only when ANVIQO_CLEANUP_TEST_ACCOUNTS=1 and the original admin
username is explicitly configured.
"""
from __future__ import annotations

import os

import anvi_tenant_store as store


def run_once() -> dict[str, object]:
    if os.getenv("ANVIQO_CLEANUP_TEST_ACCOUNTS", "").strip() != "1":
        return {"status": "SKIPPED", "reason": "cleanup flag not enabled"}

    preserve = os.getenv("ANVIQO_ADMIN_USER", "").strip()
    if not preserve:
        return {"status": "ABORTED", "reason": "ANVIQO_ADMIN_USER is required"}

    if not store.enabled():
        return {"status": "ABORTED", "reason": "tenant database is not enabled"}

    store.init_schema()
    p = store._placeholder()
    deleted_users = 0
    deleted_memberships = 0

    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT user_id, external_username FROM anviqo_users WHERE external_username <> {p}",
            (preserve,),
        )
        users = cur.fetchall()
        user_ids = [row[0] for row in users]

        if user_ids:
            for user_id in user_ids:
                cur.execute(
                    f"DELETE FROM anviqo_memberships WHERE user_id={p}",
                    (user_id,),
                )
                deleted_memberships += cur.rowcount
                # Preserve the audit trail while removing the user FK target.
                cur.execute(
                    f"UPDATE anviqo_tenant_audit SET actor_user_id=NULL WHERE actor_user_id={p}",
                    (user_id,),
                )
                cur.execute(
                    f"DELETE FROM anviqo_users WHERE user_id={p}",
                    (user_id,),
                )
                deleted_users += cur.rowcount

    return {
        "status": "DONE",
        "preserved_admin": preserve,
        "deleted_users": deleted_users,
        "deleted_memberships": deleted_memberships,
        "plant_data_touched": False,
        "pci_v5_touched": False,
    }
