"""Safe organization-scoped deletion of one plant and its onboarding data."""
from __future__ import annotations
from typing import Any
import anvi_tenant_store as store

# V1.x plant-scoped data only. Frozen V5/PCI data is never touched.
DATA_TABLES = (
    "anviqo_plant_ingestion_jobs",
    "anviqo_universal_ingestion_jobs",
    "anviqo_direct_import_jobs",
    "anviqo_plant_documents",
    "anviqo_plant_knowledge",
    "anviqo_plant_onboarding",
)

def _table_exists(cur: Any, table: str) -> bool:
    if store._is_sqlite():
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,))
    else:
        cur.execute("SELECT to_regclass(%s)", (table,))
    row = cur.fetchone()
    return bool(row and row[0] is not None)

def delete_plant(organization_id: str, plant_id: str) -> dict[str, Any]:
    if not organization_id or not plant_id:
        raise ValueError("organization_id and plant_id are required")
    p = store._placeholder()
    counts: dict[str, int] = {}
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT name,status FROM anviqo_plants WHERE plant_id={p} AND organization_id={p}", (plant_id, organization_id))
        plant = cur.fetchone()
        if not plant:
            raise LookupError("Plant not found in your organization")
        if str(plant[1]).upper() != "ACTIVE":
            raise ValueError("Plant is already inactive or unavailable")

        # The legacy anviqo_plant_ingestion_jobs table is still present in
        # production and has a direct FK to anviqo_plants. It must be purged
        # before the parent row, along with the current V1.x data tables.
        for table in DATA_TABLES:
            if not _table_exists(cur, table):
                continue
            cur.execute(f"DELETE FROM {table} WHERE plant_id={p}", (plant_id,))
            counts[table] = int(getattr(cur, "rowcount", 0) or 0)

        cur.execute(f"DELETE FROM anviqo_memberships WHERE organization_id={p} AND plant_id={p}", (organization_id, plant_id))
        counts["anviqo_memberships"] = int(getattr(cur, "rowcount", 0) or 0)

        if _table_exists(cur, "anviqo_tenant_audit"):
            cur.execute(f"DELETE FROM anviqo_tenant_audit WHERE organization_id={p} AND plant_id={p}", (organization_id, plant_id))
            counts["anviqo_tenant_audit"] = int(getattr(cur, "rowcount", 0) or 0)

        cur.execute(f"DELETE FROM anviqo_plants WHERE plant_id={p} AND organization_id={p}", (plant_id, organization_id))
        counts["anviqo_plants"] = int(getattr(cur, "rowcount", 0) or 0)
        if counts["anviqo_plants"] != 1:
            raise RuntimeError("Plant deletion did not remove exactly one plant record")
        return {"plant_id": plant_id, "plant_name": plant[0], "deleted": counts}

__all__ = ["delete_plant"]
