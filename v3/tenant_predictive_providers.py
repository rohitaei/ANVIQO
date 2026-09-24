"""Real tenant-scoped predictive evidence providers.

Backed by the normalized V1 onboarding package. This is the V3 evidence
boundary for predictive maintenance; legacy global JSON stores are not read.

No prediction, trend, diagnosis, probability, RUL, threshold, or control logic
is implemented here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from v2.tenant_evidence import SAFETY


@dataclass(frozen=True)
class TenantPredictiveProviderSet:
    package: Mapping[str, Any]

    def __post_init__(self) -> None:
        plant = self.package.get("plant") or {}
        plant_id = str(plant.get("plant_id") or "").strip()
        if not plant_id:
            raise ValueError("onboarding package plant_id is required")
        records = self.package.get("records")
        if not isinstance(records, list):
            raise ValueError("onboarding package records must be a list")
        object.__setattr__(self, "_plant_id", plant_id)
        object.__setattr__(
            self,
            "_records",
            tuple(r for r in records if isinstance(r, Mapping)),
        )

    @property
    def plant_id(self) -> str:
        return self._plant_id

    def _check(self, plant_id: str) -> None:
        if str(plant_id or "").strip() != self._plant_id:
            raise ValueError("tenant predictive evidence requested for a different plant_id")

    @staticmethod
    def _tag(record: Mapping[str, Any]) -> str:
        return str(record.get("tag") or record.get("external_id") or "").strip()

    def _matching(self, tag: str):
        wanted = str(tag or "").strip()
        return [r for r in self._records if self._tag(r) == wanted]

    def pci(self, *, plant_id: str, tag: str):
        self._check(plant_id)
        rows = self._matching(tag)
        identity = None
        live = None
        for row in rows:
            identity = identity or row.get("pci_identity")
            live = live or row.get("pci_live")
        if identity is not None:
            identity = self._row(identity, tag)
        if live is not None:
            live = self._row(live, tag)
        return identity, live

    def history(self, *, plant_id: str, tag: str):
        self._check(plant_id)
        out = []
        for row in self._matching(tag):
            values = row.get("predictive_history")
            if values is None:
                metadata = row.get("metadata")
                values = metadata.get("predictive_history") if isinstance(metadata, Mapping) else None
            if isinstance(values, list):
                out.extend(self._row(v, tag) for v in values)
        return out

    def memory(self, *, plant_id: str, tag: str):
        self._check(plant_id)
        out = []
        for row in self._matching(tag):
            values = row.get("maintenance_memory")
            if values is None:
                metadata = row.get("metadata")
                values = metadata.get("maintenance_memory") if isinstance(metadata, Mapping) else None
            if isinstance(values, list):
                out.extend(self._row(v, tag) for v in values)
        return out

    def events(self, *, plant_id: str, tag: str):
        self._check(plant_id)
        out = []
        for row in self._matching(tag):
            values = row.get("events")
            if values is None:
                metadata = row.get("metadata")
                values = metadata.get("events") if isinstance(metadata, Mapping) else None
            if isinstance(values, list):
                out.extend(self._row(v, tag) for v in values)
        return out

    def health(self, *, plant_id: str, tag: str):
        self._check(plant_id)
        for row in self._matching(tag):
            value = row.get("equipment_health")
            if value is None:
                metadata = row.get("metadata")
                value = metadata.get("equipment_health") if isinstance(metadata, Mapping) else None
            if value is not None:
                return self._row(value, tag)
        return None

    def sources(self, history_provider=None):
        from v3.predictive_sources import TenantPredictiveSources
        return TenantPredictiveSources(
            self.pci, history_provider or self.history, self.memory, self.events, self.health
        )

    @staticmethod
    def _row(value: Any, tag: str) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise ValueError("tenant predictive evidence row must be a mapping")
        row = dict(value)
        row["plant_id"] = str(row.get("plant_id") or "").strip()
        if not row["plant_id"]:
            raise ValueError("tenant predictive evidence row must carry plant_id")
        row.setdefault("tag", tag)
        return row

    def snapshot(self) -> dict[str, Any]:
        return {
            "plant_id": self._plant_id,
            "record_count": len(self._records),
            "source": "V1_NORMALIZED_ONBOARDING_PACKAGE",
            "safety": dict(SAFETY),
        }


__all__ = ["SAFETY", "TenantPredictiveProviderSet"]
