"""Tenant-safe production boundary for the canonical V3 predictive flow.

This module converts the persisted normalized onboarding records into the
package shape already consumed by V3. It never reads legacy global predictive
stores and never contains prediction logic.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from v3.predictive_package_flow import run_predictive_flow_from_package


def load_tenant_onboarding_package(
    plant_id: str,
    organization_id: str,
) -> dict[str, Any]:
    plant_id = str(plant_id or "").strip()
    organization_id = str(organization_id or "").strip()
    if not plant_id or not organization_id:
        raise ValueError("plant_id and organization_id are required")

    import anvi_tenant_store as store

    store.init_schema()
    p = store._placeholder()
    with store._connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT p.name, COALESCE(o.industry, '') "
            f"FROM anviqo_plants p "
            f"LEFT JOIN anviqo_plant_onboarding o ON o.plant_id=p.plant_id "
            f"WHERE p.plant_id={p} AND p.organization_id={p} AND p.status='ACTIVE' "
            f"LIMIT 1",
            (plant_id, organization_id),
        )
        plant = cur.fetchone()
        if not plant:
            raise PermissionError("plant is not authorized for this organization")

        cur.execute(
            f"SELECT record_type, external_id, name, area, service, asset_type, "
            f"tag, parent_id, source, metadata, content "
            f"FROM anviqo_plant_knowledge "
            f"WHERE plant_id={p} AND organization_id={p} "
            f"ORDER BY created_at",
            (plant_id, organization_id),
        )
        rows = cur.fetchall()

    records: list[dict[str, Any]] = []
    for row in rows:
        metadata = row[9]
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        if not isinstance(metadata, Mapping):
            metadata = {}

        record = {
            "record_type": row[0],
            "external_id": row[1],
            "name": row[2],
            "area": row[3],
            "service": row[4],
            "asset_type": row[5],
            "tag": row[6],
            "parent_id": row[7],
            "source": row[8],
            "metadata": dict(metadata),
            "content": row[10],
        }

        # Preserve only already-normalized tenant evidence. No global store
        # lookup or inference is performed here.
        for key in ("pci_identity", "pci_live", "predictive_history",
                    "maintenance_memory", "events", "equipment_health"):
            if key in metadata:
                record[key] = metadata[key]

        records.append(record)

    return {
        "plant": {
            "plant_id": plant_id,
            "organization_id": organization_id,
            "name": plant[0],
            "industry": plant[1],
        },
        "records": records,
    }


def run_production_predictive_flow(
    *,
    plant_id: str,
    organization_id: str,
    tag: str,
    observations: list[dict[str, Any]],
    outcome: dict[str, Any] | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
) -> dict[str, Any]:
    package = load_tenant_onboarding_package(plant_id, organization_id)

    def history_provider(*, plant_id: str, tag: str):
        from failure_prediction_history import get_tenant_observations
        return get_tenant_observations(
            plant_id=plant_id,
            organization_id=organization_id,
            tag=tag,
        )

    # When the API caller does not manually provide observations, use the
    # already-recorded tenant history as the canonical predictive evidence
    # input. This is data plumbing only; V3 still performs the same evidence
    # validation/gating and the same existing predictor invocation.
    if not observations:
        observations = history_provider(plant_id=plant_id, tag=tag)

    return run_predictive_flow_from_package(
        plant_id,
        tag,
        observations,
        package=package,
        outcome=outcome,
        window_start=window_start,
        window_end=window_end,
        history_provider=history_provider,
    )


def fetch_production_predictive_history(
    *,
    plant_id: str,
    organization_id: str,
    tag: str,
) -> dict[str, Any]:
    """Expose production history through the canonical V3 tenant bridge."""
    plant_id = str(plant_id or "").strip()
    organization_id = str(organization_id or "").strip()
    tag = str(tag or "").strip()
    if not plant_id or not organization_id or not tag:
        raise ValueError("plant_id, organization_id and tag are required")

    from failure_prediction_history import get_tenant_observations
    from v3.predictive_history_bridge import fetch_tenant_predictive_history

    def provider(*, plant_id: str, tag: str):
        return get_tenant_observations(
            plant_id=plant_id,
            organization_id=organization_id,
            tag=tag,
        )

    return fetch_tenant_predictive_history(plant_id, tag, provider=provider)


__all__ = ["load_tenant_onboarding_package", "run_production_predictive_flow", "fetch_production_predictive_history"]
