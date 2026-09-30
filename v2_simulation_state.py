"""ANVIQO V2 simulation evidence state.

Process-local, tenant-scoped evidence used only by the deterministic demo
simulation. It never writes PLC/SCADA or production plant history.
"""
from __future__ import annotations

from typing import Any

_STATE: dict[str, list[dict[str, Any]]] = {}


def record(plant_id: str, events: list[dict[str, Any]], changes: list[dict[str, Any]]) -> None:
    pid = str(plant_id or "").strip()
    if not pid:
        return
    _STATE[pid] = [
        *[dict(x, plant_id=pid) for x in events],
        *[dict(x, plant_id=pid) for x in changes],
    ]


def get(plant_id: str, tag: str | None = None) -> list[dict[str, Any]]:
    pid = str(plant_id or "").strip()
    rows = list(_STATE.get(pid, []))
    if not tag:
        return rows
    normalized = "".join(ch for ch in str(tag).upper() if ch.isalnum())
    return [
        row for row in rows
        if not row.get("equipment")
        or "".join(ch for ch in str(row.get("equipment")).upper() if ch.isalnum()) == normalized
    ]
