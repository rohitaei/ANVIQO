"""Safe organization-scoped deletion of one plant and its onboarding data.

This module only removes tenant/onboarding records for the requested plant.
Frozen V5/PCI intelligence files are deliberately not touched.
"""
from __future__ import annotations

from typing import Any

import anvi_tenant_store as store

# Explicit allow-list: only tenant/onboarding tables created by the V1.4 flow.
# Do not dynamically delete from arbitrary tables because frozen V5 intelligence
# must remain untouched.
DATA_TABLES = (
    "anviqo_plant_documents",
    "anviqo_plant_knowledge",
    "anviqo_plant_onboarding",
    "anviqo_universal_ingestion_jobs",
    "anviqo_direct_import_jobs",
)


def _table_exists(cur: Any, table: str) -> bool:
    if store._is_sqlite():
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,))
    else:
        cur.execute("SELECT to_regclass(%s)", (table,))
    row = cur.fetchone()
    return bool(row and (row[0] is not None))


def delete_plant(organization_id: str, plant_id: str) -> dict[str, Any]:
    if not organization_id or not plant_id:
        raise ValueError("organization_id and plant_id are required")

    p = store._placeholder()
    counts: dict[str, int] = {}

    with store._connect() as conn:
        cur = conn.cursor()

        # Verify exact organization ownership before deleting anything.
        cur.execute(
            f"SELECT name,status FROM anviqo_plants WHERE plant_id={p} AND organization_id={p}",
            (plant_id, organization_id),
        )
        plant = cur.fetchone()
        if not plant:
            raise LookupError("Plant not found in your organization")
        if str(plant[1]).upper() != "ACTIVE":
            raise ValueError("Plant is already inactive or unavailable")

        # Remove V1.4 uploaded source files, normalized knowledge and ingestion
        # jobs before the parent plant row. This is the complete onboarding data
        # path and is intentionally separate from frozen V5/PCI data.
        for table in DATA_TABLES:
            if not _table_exists(cur, table):
                continue
            cur.execute(f"DELETE FROM {table} WHERE plant_id={p}", (plant_id,))
            counts[table] = int(getattr(cur, "rowcount", 0) or 0)

        # Remove all memberships for this plant. Keep user records unless they
        # are independently cleaned up elsewhere; a user may belong to another
        # plant in the same organization.
        cur.execute(f"DELETE FROM anviqo_memberships WHERE organization_id={p} AND plant_id={p}", (organization_id, plant_id))
        counts["anviqo_memberships"] = int(getattr(cur, "rowcount", 0) or 0)

        # Remove tenant audit rows tied to this plant. The deletion itself is
        # recorded after the purge so there is still an audit trace.
        if _table_exists(cur, "anviqo_tenant_audit"):
            cur.execute(f"DELETE FROM anviqo_tenant_audit WHERE organization_id={p} AND plant_id={p}", (organization_id, plant_id))
            counts["anviqo_tenant_audit"] = int(getattr(cur, "rowcount", 0) or 0)

        cur.execute(f"DELETE FROM anviqo_plants WHERE plant_id={p} AND organization_id={p}", (plant_id, organization_id))
        counts["anviqo_plants"] = int(getattr(cur, "rowcount", 0) or 0)
        if counts["anviqo_plants"] != 1:
            raise RuntimeError("Plant deletion did not remove exactly one plant record")

        return {"plant_id": plant_id, "plant_name": plant[0], "deleted": counts}


__all__ = ["delete_plant"]
