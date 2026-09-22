"""Universal V2 tenant evidence provider.

Adapts the existing V1 onboarding contract into tenant-scoped evidence for
existing V5 intelligence. It never invents health/status values: V5 area
evidence is emitted only when those values are explicitly supplied by the
plant data/evidence source.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Tuple


SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


class TenantEvidenceProvider:
    """Read-only provider backed by one normalized onboarding package."""

    def __init__(self, package: Mapping[str, Any]) -> None:
        self._package = package
        plant = package.get("plant") or {}
        self._plant_id = str(plant.get("plant_id") or "").strip()
        if not self._plant_id:
            raise ValueError("onboarding package plant_id is required")
        records = package.get("records") or []
        if not isinstance(records, list):
            raise ValueError("onboarding package records must be a list")
        self._records = tuple(r for r in records if isinstance(r, Mapping))

    @property
    def plant_id(self) -> str:
        return self._plant_id

    def equipment_records(self) -> Tuple[Mapping[str, Any], ...]:
        """Return only records belonging to this provider's tenant."""
        return tuple(self._records)

    def area_evidence(self) -> list[Dict[str, Any]]:
        """Return explicit V5-compatible area evidence; never synthesize health."""
        grouped: Dict[str, Dict[str, Any]] = {}
        for record in self._records:
            area = str(record.get("area") or "").strip()
            if not area:
                continue
            metadata = record.get("metadata")
            metadata = metadata if isinstance(metadata, Mapping) else {}
            score = record.get("health_score", metadata.get("health_score"))
            status = record.get("status", metadata.get("status"))
            if score is None or not str(status or "").strip():
                continue
            bucket = grouped.setdefault(area, {
                "plant_id": self._plant_id,
                "area": area,
                "health_score": score,
                "status": str(status).strip(),
                "equipment": [],
            })
            tag = str(record.get("tag") or record.get("external_id") or "").strip()
            if tag:
                bucket["equipment"].append({
                    "tag": tag,
                    "name": record.get("name", ""),
                    "asset_type": record.get("asset_type", ""),
                })
        return list(grouped.values())

    def __call__(self, plant_id: str) -> list[Dict[str, Any]]:
        requested = str(plant_id or "").strip()
        if requested != self._plant_id:
            raise ValueError("tenant evidence requested for a different plant_id")
        return self.area_evidence()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "plant_id": self._plant_id,
            "record_count": len(self._records),
            "area_evidence_count": len(self.area_evidence()),
            "safety": dict(SAFETY),
            "source": "V2_TENANT_EVIDENCE_PROVIDER",
        }


__all__ = ["SAFETY", "TenantEvidenceProvider"]
