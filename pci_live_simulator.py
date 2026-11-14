"""
ANVIQO PCI LIVE SIMULATOR
==========================
Demo-mode simulation of the existing 1,064 PCI I/O records.

IMPORTANT:
- Uses ONLY the existing PCI database.
- Does NOT create fake equipment identities.
- Does NOT write to PLC/SCADA.
- Does NOT alter V5 reasoning.
- Clearly represents SIMULATION / DEMO MODE.
"""

import json
import os
import random
import time
from datetime import datetime, timezone

PCI_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "database", "pci", "pci_instrument_database.json"
)

_rng = random.Random(20260813)
_SIMULATION_WINDOW_TIMESTAMP = None
# Keep one deterministic simulation snapshot stable briefly so conversational
# questions in the same observation window see the same plant state.
_SNAPSHOT_CACHE = None
_SNAPSHOT_CACHE_AT = 0.0
_SNAPSHOT_CACHE_TTL = 15.0


def load_pci_records():
    with open(PCI_DB, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])

    if not isinstance(records, list):
        raise ValueError("PCI records are not a list")

    return records


def _value_for_io(record):
    io_type = str(record.get("io_type", "")).upper()

    if io_type == "DI":
        return _rng.choice([0, 1])

    if io_type == "DO":
        return _rng.choice([0, 1])

    if io_type == "AI":
        return round(_rng.uniform(0, 100), 2)

    if io_type == "AO":
        return round(_rng.uniform(0, 100), 2)

    return round(_rng.uniform(0, 100), 2)


def _state(record, value):
    """Assess only against explicitly approved signal configuration.

    Missing limits/semantics are not evidence of a healthy or failed point.
    """
    io_type = str(record.get("io_type", "")).upper()
    if io_type in ("AI", "AO") or "4-20MA" in io_type or "RTD" in io_type:
        limits = record.get("approved_engineering_limits")
        if not isinstance(limits, dict) or limits.get("approved") is not True:
            return "UNASSESSED"
        try:
            low = float(limits["low"])
            high = float(limits["high"])
            critical_low = float(limits.get("critical_low", low))
            critical_high = float(limits.get("critical_high", high))
            warning_low = float(limits.get("warning_low", low))
            warning_high = float(limits.get("warning_high", high))
            measured = float(value)
        except (KeyError, TypeError, ValueError):
            return "UNASSESSED"
        if not (low <= critical_low <= warning_low <= warning_high <= critical_high <= high):
            return "UNASSESSED"
        if measured < critical_low or measured > critical_high:
            return "CRITICAL"
        if measured < warning_low or measured > warning_high:
            return "WARNING"
        return "HEALTHY"

    if io_type in ("DI", "DO"):
        semantics = record.get("approved_signal_semantics")
        if not isinstance(semantics, dict) or semantics.get("approved") is not True:
            return "UNASSESSED"
        normal_states = semantics.get("normal_states")
        alarm_states = semantics.get("alarm_states")
        if not isinstance(normal_states, list) or not isinstance(alarm_states, list):
            return "UNASSESSED"
        if value in normal_states:
            return "HEALTHY"
        if value in alarm_states:
            return "WARNING"
    return "UNASSESSED"


def reset_simulation_window(window=None):
    """Reset demo values to a repeatable seed for one UTC minute window."""
    global _rng, _SIMULATION_WINDOW_TIMESTAMP
    if window is None:
        window = int(time.time() // 60)
    window = int(window)
    _rng = random.Random(20260813 + window)
    _SIMULATION_WINDOW_TIMESTAMP = datetime.fromtimestamp(
        window * 60, timezone.utc
    ).isoformat()
    return window, _SIMULATION_WINDOW_TIMESTAMP


def simulate_point(record):
    value = _value_for_io(record)
    state = _state(record, value)

    return {
        "tag": record.get("tag", ""),
        "description": record.get("description", ""),
        "area": record.get("area", ""),
        "io_type": record.get("io_type", ""),
        "plc_address": record.get("plc_address", ""),
        "panel": record.get("panel", ""),
        "value": value,
        "state": state,
        "changed": False,
        # Synthetic values are not event/alarm evidence. A separate,
        # explicitly configured event source is required for these flags.
        "event_active": False,
        "value_basis": "SYNTHETIC_DEMO_VALUE_NOT_ENGINEERING_MEASUREMENT",
        "assessment_basis": (
            "APPROVED_SIGNAL_CONFIGURATION"
            if state in ("HEALTHY", "WARNING", "CRITICAL")
            else "NO_APPROVED_SIGNAL_LIMITS_OR_STATE_SEMANTICS"
        ),
        "timestamp": _SIMULATION_WINDOW_TIMESTAMP or datetime.now(timezone.utc).isoformat(),
        "mode": "SIMULATION",
        "source": "PCI DEMO STREAM",
    }


def simulate_snapshot():
    window, snapshot_timestamp = reset_simulation_window()
    records = load_pci_records()

    points = [
        simulate_point(record)
        for record in records
    ]

    healthy = sum(
        1 for p in points if p["state"] == "HEALTHY"
    )

    warning = sum(
        1 for p in points if p["state"] == "WARNING"
    )

    critical = sum(
        1 for p in points if p["state"] == "CRITICAL"
    )
    unassessed = sum(1 for p in points if p["state"] == "UNASSESSED")

    changed = sum(
        1 for p in points if p["changed"]
    )

    active_events = sum(
        1 for p in points if p["event_active"]
    )

    areas = {}

    for point in points:
        area = point["area"] or "UNKNOWN"

        areas.setdefault(
            area,
            {
                "area": area,
                "total": 0,
                "healthy": 0,
                "warning": 0,
                "critical": 0,
                "unassessed": 0,
            },
        )

        areas[area]["total"] += 1

        if point["state"] == "HEALTHY":
            areas[area]["healthy"] += 1
        elif point["state"] == "WARNING":
            areas[area]["warning"] += 1
        elif point["state"] == "CRITICAL":
            areas[area]["critical"] += 1
        else:
            areas[area]["unassessed"] += 1

    for area in areas.values():
        total = area["total"]

        assessed = area["healthy"] + area["warning"] + area["critical"]
        score = (
            (area["healthy"] + area["warning"] * 0.5) / assessed * 100
            if total and assessed == total else None
        )
        area["health_score"] = round(score, 2) if score is not None else None

    assessed_count = healthy + warning + critical
    plant_score = (
        ((healthy + warning * 0.5) / assessed_count) * 100
        if points and assessed_count == len(points) else None
    )

    return {
        "snapshot_id": f"PCI-DEMO-{window}",
        "observation_window_seconds": 60,
        "mode": "SIMULATION",
        "source": "PCI DEMO STREAM",
        "timestamp": snapshot_timestamp,
        "total_io": len(points),
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "unassessed": unassessed,
        "assessed": assessed_count,
        "changed": changed,
        "active_events": active_events,
        "plant_health_score": round(plant_score, 2) if plant_score is not None else None,
        "area_count": len(areas),
        "areas": list(areas.values()),
        "points": points,
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "human_decision_required": True,
    }


def get_live_pci_snapshot():
    global _SNAPSHOT_CACHE, _SNAPSHOT_CACHE_AT
    now = time.monotonic()
    if _SNAPSHOT_CACHE is None or (now - _SNAPSHOT_CACHE_AT) >= _SNAPSHOT_CACHE_TTL:
        _SNAPSHOT_CACHE = simulate_snapshot()
        _SNAPSHOT_CACHE_AT = now
    return _SNAPSHOT_CACHE


if __name__ == "__main__":
    snapshot = simulate_snapshot()

    print("===== ANVIQO PCI LIVE SIMULATOR =====")
    print("MODE:", snapshot["mode"])
    print("SOURCE:", snapshot["source"])
    print("TOTAL I/O:", snapshot["total_io"])
    print("HEALTHY:", snapshot["healthy"])
    print("WARNING:", snapshot["warning"])
    print("CRITICAL:", snapshot["critical"])
    print("UNASSESSED:", snapshot["unassessed"])
    print("CHANGED:", snapshot["changed"])
    print("ACTIVE EVENTS:", snapshot["active_events"])
    print("AREAS:", snapshot["area_count"])
    print("PLANT HEALTH:", snapshot["plant_health_score"])
    print("======================================")
