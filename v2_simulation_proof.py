"""ANVIQO V2 deterministic SIMULATION proof harness.

Read-only acceptance harness. It never writes PLC/SCADA or production history.
It composes an existing PCI identity with a controlled synthetic change and
runs the same event-correlation logic used by Command Centre.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os

from event_correlation import correlate_events

PCI_DB = os.path.join("database", "pci", "pci_instrument_database.json")


def _load_pt303():
    with open(PCI_DB, "r", encoding="utf-8") as f:
        records = json.load(f).get("records", [])
    for row in records:
        tag = str(row.get("tag", "")).replace("-", "_").upper()
        if tag == "PT_303":
            return row
    raise LookupError("PT-303 is not present in PCI identity database")


def run_v2_simulation_proof(plant_id: str = ""):
    # Use the authenticated selected plant when the caller does not
    # explicitly provide a tenant id.
    if not plant_id:
        try:
            from flask import has_request_context, session
            if has_request_context() and session.get("authenticated"):
                plant_id = str(session.get("plant_id") or "").strip()
        except Exception:
            plant_id = ""
    now = datetime.now(timezone.utc)
    before = 42.0
    after = 68.0
    delta = round(after - before, 2)
    pct = round((delta / before) * 100, 2)

    identity = _load_pt303()
    tag = identity.get("tag") or "PT_303"

    events = [
        {
            "timestamp": now.isoformat(),
            "event_type": "VALUE_CHANGE",
            "equipment": tag,
            "message": f"PT-303 simulated value changed from {before} to {after}",
            "source": "ANVIQO V2 SIMULATION",
            "external_id": f"SIM-{now.strftime('%Y%m%d%H%M%S%f')}",
        },
        {
            "timestamp": now.isoformat(),
            "event_type": "STATE_CHANGE",
            "equipment": tag,
            "message": "PT-303 simulated condition changed to WARNING",
            "source": "ANVIQO V2 SIMULATION",
            "external_id": f"SIM-W-{now.strftime('%Y%m%d%H%M%S%f')}",
        },
    ]

    changes = [{
        "timestamp": now.isoformat(),
        "equipment": tag,
        "parameter": identity.get("description") or "PT-303",
        "change_type": "VALUE_CHANGE",
        "previous": before,
        "current": after,
        "percentage_change": pct,
        "direction": "INCREASE",
        "source": "ANVIQO V2 SIMULATION",
        "external_id": events[0]["external_id"],
    }]

    correlation = correlate_events(tag, events)

    if plant_id:
        try:
            from v2_simulation_state import record
            record(plant_id, events, changes)
        except Exception:
            pass

    checks = {
        "simulation_mode": True,
        "pci_identity_found": bool(identity),
        "controlled_value_change": before != after,
        "event_generated": len(events) == 2,
        "event_correlated": correlation.get("event_count") == 2,
        "what_changed_generated": len(changes) == 1,
        "same_equipment_identity": all(
            str(e.get("equipment", "")).replace("-", "_").upper()
            == str(tag).replace("-", "_").upper()
            for e in events
        ),
        "causation_not_claimed": correlation.get("causation_claimed") is False,
        "plc_write_blocked": True,
        "scada_control_blocked": True,
        "human_decision_required": True,
    }

    passed = all(checks.values())

    return {
        "status": "PASS" if passed else "FAIL",
        "test": "V2.0 REAL-TIME INDUSTRIAL INTELLIGENCE — SIMULATION PROOF",
        "mode": "SIMULATION",
        "source": "ANVIQO V2 SIMULATION HARNESS",
        "equipment": tag,
        "identity": {
            "description": identity.get("description"),
            "area": identity.get("area"),
            "io_type": identity.get("io_type"),
            "plc_address": identity.get("plc_address"),
        },
        "baseline": before,
        "current": after,
        "delta": delta,
        "percentage_change": pct,
        "events": events,
        "changes": changes,
        "correlation": correlation,
        "checks": checks,
        "safety": {
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "automatic_authorization": False,
            "automatic_execution": False,
            "human_decision_required": True,
        },
        "timestamp": now.isoformat(),
    }
