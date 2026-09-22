"""Universal V2 discovery orchestration.

Turns generic WATCH evidence into investigation candidates. It does not decide
anomaly, alarm, diagnosis, prediction, or failure; existing V5 intelligence
remains authoritative for those decisions.
"""
from __future__ import annotations
from typing import Any
from .watch import WatchSnapshot

SAFETY = {
    "read_only": True, "plc_write": False, "scada_control": False,
    "automatic_action": False, "human_decision_required": True,
}

def discover(plant_id: str, snapshot: WatchSnapshot) -> dict[str, Any]:
    if snapshot.plant_id != plant_id:
        raise ValueError("watch snapshot plant_id does not match plant_id")
    candidates = []
    for item in snapshot.candidates:
        row = dict(item)
        row["plant_id"] = plant_id
        row["classification"] = "DISCOVERY_CANDIDATE"
        row["is_alarm"] = False
        row["is_diagnosis"] = False
        candidates.append(row)
    return {
        "plant_id": plant_id,
        "state": snapshot.state,
        "candidates": candidates,
        "safety": dict(SAFETY),
        "source": "V2_WATCH_DISCOVERY",
    }
