"""V2 read-only source adapter interfaces and the existing PCI demo adapter.

Adapters own transport/normalization only. They do not perform prediction,
root-cause analysis, alarm decisions, authorization, or PLC/SCADA writes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Iterable, Iterator, Mapping

from .contracts import IndustrialPoint
from .data_fabric import normalize_simulation_point


class ReadOnlySourceAdapter(ABC):
    """Transport-neutral contract for a read-only industrial source."""

    name = "UNNAMED"
    mode = "UNKNOWN"

    @abstractmethod
    def read(self, plant_id: str) -> Iterable[IndustrialPoint]:
        """Yield normalized points for exactly one plant."""
        raise NotImplementedError


class IndustrialPointSourceAdapter(ReadOnlySourceAdapter):
    """Universal seam for a real read-only source returning IndustrialPoints.

    The transport is deliberately supplied by the caller. This class performs
    only source-boundary validation and normalization checks; it does not
    implement OPC UA, MQTT, Modbus, PLC polling, or any prediction logic.
    """

    mode = "LIVE"

    def __init__(
        self,
        reader: Callable[[str], Iterable[IndustrialPoint]],
        *,
        name: str = "READ-ONLY SOURCE",
        mode: str = "LIVE",
    ) -> None:
        if not callable(reader):
            raise TypeError("reader must be callable")
        self._reader = reader
        self.name = str(name or "READ-ONLY SOURCE").strip()
        self.mode = str(mode or "LIVE").strip()

    def read(self, plant_id: str) -> Iterator[IndustrialPoint]:
        plant_id = str(plant_id or "").strip()
        if not plant_id:
            raise ValueError("plant_id is required")

        for point in self._reader(plant_id):
            if not isinstance(point, IndustrialPoint):
                raise TypeError("source reader must yield IndustrialPoint values")
            if point.plant_id != plant_id:
                raise ValueError("cross-plant IndustrialPoint rejected")
            source_text = f"{point.source} {point.mode}".upper()
            if "SIMULATION" in source_text or "DEMO" in source_text:
                raise ValueError("simulation/demo source is not eligible for live ingestion")
            if not point.tag.strip():
                raise ValueError("tag is required")
            if not point.timestamp.strip():
                raise ValueError("timestamp is required")
            if not point.source.strip():
                raise ValueError("source is required")
            yield point


class PciDemoStreamAdapter(ReadOnlySourceAdapter):
    """Bridge the existing PCI simulator into the V2 IndustrialPoint contract."""

    name = "PCI DEMO STREAM"
    mode = "SIMULATION"

    def __init__(self, snapshot_getter=None) -> None:
        self._snapshot_getter = snapshot_getter

    def _getter(self):
        if self._snapshot_getter is not None:
            return self._snapshot_getter
        from pci_live_simulator import get_live_pci_snapshot
        return get_live_pci_snapshot

    def read(self, plant_id: str) -> Iterator[IndustrialPoint]:
        plant_id = str(plant_id or "").strip()
        if not plant_id:
            raise ValueError("plant_id is required")
        snapshot = self._getter()()
        for raw in snapshot.get("points", []):
            point = normalize_simulation_point(raw, plant_id)
            if not point.tag:
                continue
            yield point


class FabricSourceRunner:
    """Small composition helper: source -> normalized points -> data fabric."""

    def __init__(self, fabric, adapter: ReadOnlySourceAdapter) -> None:
        self.fabric = fabric
        self.adapter = adapter

    def poll_once(self, plant_id: str) -> int:
        return self.fabric.ingest_many(self.adapter.read(plant_id))


def pci_demo_adapter() -> PciDemoStreamAdapter:
    """Factory kept separate so future OPC UA/MQTT/Historian adapters are peers."""
    return PciDemoStreamAdapter()
