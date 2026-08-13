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
    "database", "pci", "pci_instrument_database.json"
)

_rng = random.Random(20260813)


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


def _state():
    n = _rng.random()

    if n < 0.88:
        return "HEALTHY"

    if n < 0.975:
        return "WARNING"

    return "CRITICAL"


def simulate_point(record):
    state = _state()

    return {
        "tag": record.get("tag", ""),
        "description": record.get("description", ""),
        "area": record.get("area", ""),
        "io_type": record.get("io_type", ""),
        "plc_address": record.get("plc_address", ""),
        "panel": record.get("panel", ""),
        "value": _value_for_io(record),
        "state": state,
        "changed": _rng.random() < 0.06,
        "event_active": state in ("WARNING", "CRITICAL")
        and _rng.random() < 0.55,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "SIMULATION",
        "source": "PCI DEMO STREAM",
    }


def simulate_snapshot():
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
            },
        )

        areas[area]["total"] += 1

        if point["state"] == "HEALTHY":
            areas[area]["healthy"] += 1
        elif point["state"] == "WARNING":
            areas[area]["warning"] += 1
        else:
            areas[area]["critical"] += 1

    for area in areas.values():
        total = area["total"]

        score = (
            (
                area["healthy"]
                + area["warning"] * 0.5
            )
            / total
        ) * 100 if total else 0

        area["health_score"] = round(score, 2)

    plant_score = (
        (
            healthy
            + warning * 0.5
        )
        / len(points)
    ) * 100 if points else 0

    return {
        "mode": "SIMULATION",
        "source": "PCI DEMO STREAM",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_io": len(points),
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "changed": changed,
        "active_events": active_events,
        "plant_health_score": round(plant_score, 2),
        "area_count": len(areas),
        "areas": list(areas.values()),
        "points": points,
    }


def get_live_pci_snapshot():
    return simulate_snapshot()


if __name__ == "__main__":
    snapshot = simulate_snapshot()

    print("===== ANVIQO PCI LIVE SIMULATOR =====")
    print("MODE:", snapshot["mode"])
    print("SOURCE:", snapshot["source"])
    print("TOTAL I/O:", snapshot["total_io"])
    print("HEALTHY:", snapshot["healthy"])
    print("WARNING:", snapshot["warning"])
    print("CRITICAL:", snapshot["critical"])
    print("CHANGED:", snapshot["changed"])
    print("ACTIVE EVENTS:", snapshot["active_events"])
    print("AREAS:", snapshot["area_count"])
    print("PLANT HEALTH:", snapshot["plant_health_score"])
    print("======================================")
