"""Tenant-scoped adapter for verified PCI evidence.

The bundled PCI registry is not a global chat fallback. A plant must have an
explicit evidence binding before its records can enter the tenant resolver.
The adapter is read-only and reuses the frozen PCI resolver.
"""
from __future__ import annotations

import os
import re
from typing import Any

BINDING_TABLE = "anviqo_plant_evidence_bindings"


def _store():
    import anvi_tenant_store as store
    return store if store.enabled() else None


def _ensure_binding_table(store):
    p = store._placeholder()
    if store._is_sqlite():
        sql = (
            f"CREATE TABLE IF NOT EXISTS {BINDING_TABLE} ("
            "plant_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, "
            "dataset_key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE', "
            "created_at TEXT NOT NULL)"
        )
    else:
        sql = (
            f"CREATE TABLE IF NOT EXISTS {BINDING_TABLE} ("
            "plant_id TEXT PRIMARY KEY REFERENCES anviqo_plants(plant_id), "
            "organization_id TEXT NOT NULL REFERENCES anviqo_organizations(organization_id), "
            "dataset_key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE', "
            "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
        )
    with store._connect() as conn:
        conn.cursor().execute(sql)


def _ensure_bootstrap_binding(store, plant_id, organization_id):
    """Bind only the original ANVIQO bootstrap plant to the bundled PCI source.

    This is an explicit dataset binding, not a cross-plant fallback. New plants
    are not bound automatically and therefore cannot see this dataset.
    """
    p = store._placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT 1 FROM {BINDING_TABLE} WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE'",
            (plant_id, organization_id),
        )
        if cur.fetchone():
            return True
        cur.execute(
            f"SELECT p.plant_id,o.slug FROM anviqo_plants p "
            f"JOIN anviqo_organizations o ON o.organization_id=p.organization_id "
            f"WHERE p.plant_id={p} AND p.organization_id={p} "
            f"AND p.slug='primary-plant' AND o.slug='anviqo-customer' AND p.status='ACTIVE'",
            (plant_id, organization_id),
        )
        if not cur.fetchone():
            return False
        if store._is_sqlite():
            cur.execute(
                f"INSERT OR IGNORE INTO {BINDING_TABLE}(plant_id,organization_id,dataset_key,status,created_at) "
                f"VALUES({p},{p},{p},'ACTIVE',{p})",
                (plant_id, organization_id, "pci-master-v1", store._now()),
            )
        else:
            cur.execute(
                f"INSERT INTO {BINDING_TABLE}(plant_id,organization_id,dataset_key,status) "
                f"VALUES({p},{p},{p},'ACTIVE') ON CONFLICT(plant_id) DO NOTHING",
                (plant_id, organization_id, "pci-master-v1"),
            )
    return True


def is_bound(plant_id: str, organization_id: str | None = None) -> bool:
    store = _store()
    if not store or not plant_id:
        return False
    try:
        store.init_schema()
        _ensure_binding_table(store)
        _ensure_bootstrap_binding(store, plant_id, organization_id)
        p = store._placeholder()
        with store._connect() as conn:
            cur = conn.cursor()
            if organization_id:
                cur.execute(
                    f"SELECT 1 FROM {BINDING_TABLE} WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE'",
                    (plant_id, organization_id),
                )
            else:
                cur.execute(
                    f"SELECT 1 FROM {BINDING_TABLE} WHERE plant_id={p} AND status='ACTIVE'",
                    (plant_id,),
                )
            return bool(cur.fetchone())
    except Exception as exc:
        print(f"ANVIQO_PCI_BINDING_CHECK_ERROR error={exc!r}", flush=True)
        return False


def _registry_rows():
    """Return every verified PCI source row with a stable physical identity.

    Normal tags keep their historical external_id. Repeated tag names in the
    same source sheet receive a deterministic physical suffix so distinct I/O
    points are not collapsed by tenant uniqueness.
    """
    from pci_registry import load_records
    rows = []
    seen = {}
    for row_index, r in enumerate(load_records(), start=1):
        raw_tag = str(r.get("tag") or "").strip()
        # A few verified source rows have no conventional tag. Preserve them
        # rather than dropping source records: use the documented Fox PLC tag
        # when present, otherwise a deterministic source-row identity.
        tag = raw_tag or str(r.get("fox_plc_tag") or "").strip() or f"SOURCE_ROW_{row_index}"
        source = str(r.get("source_sheet") or "pci_instrument_database.json").strip()
        metadata = {
            "fox_plc_tag": r.get("fox_plc_tag", ""),
            "io_type": r.get("io_type", ""),
            "plc_address": r.get("plc_address", ""),
            "panel": r.get("panel", ""),
            "tb": r.get("tb_name", ""),
            "tb_no": r.get("tb_no", ""),
            "jb": r.get("jb_name", ""),
            "jb_no": r.get("jb_no", ""),
            "range": r.get("range", ""),
            "unit": r.get("unit", ""),
            "model": r.get("model", ""),
            "criticality": r.get("criticality", ""),
            "process_role": r.get("process_role", ""),
            "field_elec": r.get("field_elec", ""),
            "source_sheet": source,
        }
        base_key = (tag, source)
        ordinal = seen.get(base_key, 0) + 1
        seen[base_key] = ordinal
        external_id = tag
        if ordinal > 1:
            # Use the immutable source-row ordinal for repeated tags. This is
            # deliberately stronger than a physical-field digest: even two
            # source rows that are identical in every field remain separate.
            # The first occurrence keeps its historical tag-based external_id;
            # repeated occurrences receive a deterministic source-row identity.
            external_id = f"{tag}__SRCROW_{row_index}"
        rows.append({
            "tag": tag,
            "external_id": external_id,
            "name": r.get("description", ""),
            "area": r.get("area", ""),
            "service": r.get("description", ""),
            "asset_type": "instrument",
            "record_type": "PCI_VERIFIED",
            "source": source,
            "content": r.get("description", ""),
            "metadata": {k: v for k, v in metadata.items() if v not in (None, "")},
        })
    return rows


def resolve_for_bound_plant(plant_id: str, organization_id: str | None, query: str) -> list[dict[str, Any]]:
    """Resolve bundled PCI evidence only when bound to this exact plant."""
    if not is_bound(plant_id, organization_id):
        return []
    try:
        from pci_universal_resolver import resolve
        rows = _registry_rows()
        records = []
        for row in rows:
            meta = row["metadata"]
            records.append({
                "tag": row["tag"],
                "fox_plc_tag": str(meta.get("plc_tag") or ""),
                "description": row["name"] or row["service"],
                "io_type": str(meta.get("io_type") or ""),
                "plc_address": str(meta.get("plc_address") or ""),
                "panel": str(meta.get("panel") or ""),
                "tb_name": str(meta.get("tb") or ""),
                "tb_no": str(meta.get("tb_no") or ""),
                "jb_name": str(meta.get("jb") or ""),
                "jb_no": str(meta.get("jb_no") or ""),
                "source_sheet": str(meta.get("source_sheet") or row["source"]),
                "_universal_row": row,
            })
        resolved, _match = resolve(query, records)
        if not resolved:
            return []
        out = []
        seen = set()
        for hit in resolved:
            row = dict(hit.get("_universal_row") or {})
            identity = re.sub(r"[^A-Z0-9]+", "", str(row.get("tag") or "").upper())
            if identity and identity not in seen:
                row["evidence_scope"] = "BOUND_PLANT_VERIFIED_PCI"
                row["evidence_read_only"] = True
                row["plant_id"] = plant_id
                row["organization_id"] = organization_id or ""
                out.append(row)
                seen.add(identity)
        return out
    except Exception as exc:
        print(f"ANVIQO_PCI_ADAPTER_RESOLVE_ERROR error={exc!r}", flush=True)
        return []


def bind_dataset(plant_id: str, organization_id: str, dataset_key: str = "pci-master-v1") -> bool:
    """Explicit admin/deployment hook for binding a verified dataset to a plant."""
    store = _store()
    if not store or not plant_id or not organization_id:
        return False
    store.init_schema()
    _ensure_binding_table(store)
    p = store._placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT 1 FROM anviqo_plants WHERE plant_id={p} AND organization_id={p} AND status='ACTIVE'",
            (plant_id, organization_id),
        )
        if not cur.fetchone():
            return False
        if store._is_sqlite():
            cur.execute(
                f"INSERT OR REPLACE INTO {BINDING_TABLE}(plant_id,organization_id,dataset_key,status,created_at) "
                f"VALUES({p},{p},{p},'ACTIVE',{p})",
                (plant_id, organization_id, dataset_key, store._now()),
            )
        else:
            cur.execute(
                f"INSERT INTO {BINDING_TABLE}(plant_id,organization_id,dataset_key,status) "
                f"VALUES({p},{p},{p},'ACTIVE') "
                f"ON CONFLICT(plant_id) DO UPDATE SET organization_id=EXCLUDED.organization_id,dataset_key=EXCLUDED.dataset_key,status='ACTIVE'",
                (plant_id, organization_id, dataset_key),
            )
    return True
