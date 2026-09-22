"""Universal read-only bridge for supplied alarm evidence.

This module never creates alarm thresholds or alarm decisions. It normalizes
explicit source alarms and optionally forwards them to an existing V5 handler.
"""
from __future__ import annotations
from typing import Any, Callable, Iterable, Optional

SAFETY = {
    "read_only": True, "plc_write": False, "scada_control": False,
    "automatic_action": False, "human_decision_required": True,
}

def normalize_alarms(plant_id: str, alarms: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result=[]
    for alarm in alarms:
        if not isinstance(alarm, dict):
            continue
        row=dict(alarm)
        supplied=str(row.get("plant_id") or plant_id).strip()
        if supplied != plant_id:
            raise ValueError("alarm evidence plant_id does not match plant_id")
        row["plant_id"]=plant_id
        result.append(row)
    return result

def run_alarm_bridge(
    plant_id: str,
    alarms: Iterable[dict[str, Any]],
    v5_handler: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    normalized=normalize_alarms(plant_id, alarms)
    if v5_handler is None:
        return {"plant_id":plant_id,"status":"NOT_INVOKED","alarms":normalized,
                "safety":dict(SAFETY)}
    result=v5_handler(plant_id, normalized)
    return {"plant_id":plant_id,"status":"INVOKED","alarms":normalized,
            "result":result,"safety":dict(SAFETY)}
