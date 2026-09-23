"""Tenant-safe source contract for the existing ANVIQO predictor.

This module contains no prediction logic. It validates that every data source
used by the existing predictor explicitly accepts plant_id and returns rows
that remain inside that plant scope.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}

Provider = Callable[..., Any]


@dataclass(frozen=True)
class TenantPredictiveSources:
    pci: Provider
    history: Provider
    memory: Provider
    events: Provider
    health: Provider


def _requires_plant_id(provider: Provider, name: str) -> None:
    try:
        parameters = inspect.signature(provider).parameters
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} provider signature could not be verified") from exc
    if "plant_id" not in parameters:
        raise ValueError(f"{name} provider must explicitly declare plant_id")


def validate_sources(sources: TenantPredictiveSources) -> TenantPredictiveSources:
    if not isinstance(sources, TenantPredictiveSources):
        raise TypeError("sources must be TenantPredictiveSources")
    for name in ("pci", "history", "memory", "events", "health"):
        _requires_plant_id(getattr(sources, name), name)
    return sources


def _validate_row(row: dict[str, Any], plant_id: str, tag: str, name: str) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError(f"{name} source returned a non-dictionary row")
    row_plant = row.get("plant_id")
    if row_plant is None or str(row_plant) != plant_id:
        raise ValueError(f"{name} source returned cross-plant evidence")
    row_tag = row.get("tag")
    if row_tag is not None and str(row_tag) != tag:
        raise ValueError(f"{name} source returned a tag mismatch")
    return row


def fetch(sources: TenantPredictiveSources, plant_id: str, tag: str) -> dict[str, Any]:
    validate_sources(sources)
    plant_id = str(plant_id or "").strip()
    tag = str(tag or "").strip()
    if not plant_id or not tag:
        raise ValueError("plant_id and tag are required")

    identity, live = sources.pci(plant_id=plant_id, tag=tag)
    if identity is not None:
        _validate_row(identity, plant_id, tag, "pci identity")
    if live is not None:
        _validate_row(live, plant_id, tag, "pci live")

    history = sources.history(plant_id=plant_id, tag=tag)
    memory = sources.memory(plant_id=plant_id, tag=tag)
    events = sources.events(plant_id=plant_id, tag=tag)
    health = sources.health(plant_id=plant_id, tag=tag)

    for name, rows in (("history", history), ("memory", memory), ("events", events)):
        if not isinstance(rows, list):
            raise ValueError(f"{name} source must return a list")
        for row in rows:
            _validate_row(row, plant_id, tag, name)

    if health is not None:
        _validate_row(health, plant_id, tag, "health")

    return {
        "identity": identity,
        "live": live,
        "history": history,
        "memory": memory,
        "events": events,
        "health": health,
        "safety": dict(SAFETY),
    }
