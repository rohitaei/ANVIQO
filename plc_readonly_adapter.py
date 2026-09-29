"""ANVIQO read-only live PLC adapter contract.

Simulation-first connector boundary for future Siemens/OPC/gateway integrations.
This module carries observations only; it contains no PLC/SCADA write capability
and does not create a second reasoning engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "automatic_authorization": False,
    "automatic_execution": False,
}

MODE_SIMULATION = "SIMULATION"
MODE_LIVE = "LIVE"


class AdapterValidationError(ValueError):
    """Raised when an observation does not satisfy the ANVIQO contract."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize_observation(
    record: Mapping[str, Any],
    *,
    plant_id: str,
    source: str = "ANVIQO_SIMULATION",
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Normalize one PLC observation without changing its engineering meaning."""
    if not plant_id:
        raise AdapterValidationError("plant_id is required")

    tag = str(record.get("tag") or record.get("external_id") or "").strip()
    if not tag:
        raise AdapterValidationError("tag is required")

    value = record.get("value")
    if value is None and "engineering_value" in record:
        value = record.get("engineering_value")
    if value is None:
        raise AdapterValidationError(f"value is required for {tag}")

    quality = str(record.get("quality") or "GOOD").upper().strip()
    if quality not in {"GOOD", "BAD", "UNCERTAIN"}:
        raise AdapterValidationError(f"invalid quality for {tag}: {quality}")

    timestamp = observed_at or record.get("timestamp") or _utc_now()
    result = {
        "plant_id": plant_id,
        "tag": tag,
        "external_id": str(record.get("external_id") or tag),
        "description": record.get("description"),
        "value": value,
        "raw_value": record.get("raw_value"),
        "engineering_value": record.get("engineering_value", value),
        "unit": record.get("unit"),
        "quality": quality,
        "timestamp": timestamp,
        "plc": record.get("plc"),
        "address": record.get("address"),
        "data_type": record.get("data_type"),
        "scaling": record.get("scaling"),
        "area": record.get("area"),
        "source": source,
        "mode": record.get("mode", MODE_SIMULATION),
        "safety": dict(SAFETY),
    }
    return result


def normalize_batch(
    records: Iterable[Mapping[str, Any]],
    *,
    plant_id: str,
    source: str = "ANVIQO_SIMULATION",
) -> list[dict[str, Any]]:
    """Normalize a bounded batch of observations for cloud ingestion."""
    return [
        normalize_observation(item, plant_id=plant_id, source=source)
        for item in records
    ]


def build_simulation_snapshot(
    *,
    plant_id: str = "DEMO_PLANT",
    source: str = "ANVIQO_PLC_SIMULATION",
) -> dict[str, Any]:
    """Produce deterministic demo PLC observations for end-to-end testing."""
    samples = [
        {
            "tag": "PT-303",
            "external_id": "PT_303",
            "description": "Mill outlet Gas Pressure",
            "value": 1.82,
            "engineering_value": 1.82,
            "unit": "bar",
            "quality": "GOOD",
            "plc": "SIM-S7-400H",
            "address": "PIW 260",
            "data_type": "AI",
            "area": "VRM/MILL",
        },
        {
            "tag": "PT-402",
            "external_id": "PT_402",
            "description": "Demo process pressure",
            "value": 2.14,
            "engineering_value": 2.14,
            "unit": "bar",
            "quality": "GOOD",
            "plc": "SIM-S7-400H",
            "address": "PIW 402",
            "data_type": "AI",
            "area": "GAS/PROCESS",
        },
        {
            "tag": "PT-403",
            "external_id": "PT_403",
            "description": "Demo process pressure",
            "value": 2.08,
            "engineering_value": 2.08,
            "unit": "bar",
            "quality": "GOOD",
            "plc": "SIM-S7-400H",
            "address": "PIW 404",
            "data_type": "AI",
            "area": "GAS/PROCESS",
        },
    ]
    observations = normalize_batch(samples, plant_id=plant_id, source=source)
    return {
        "status": "OK",
        "mode": MODE_SIMULATION,
        "source": source,
        "plant_id": plant_id,
        "timestamp": _utc_now(),
        "observations": observations,
        "count": len(observations),
        "safety": dict(SAFETY),
    }


def validate_live_enablement(config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate future live transport configuration without opening a socket."""
    protocol = str(config.get("protocol") or "").strip().upper()
    if protocol not in {"S7", "OPC_UA", "OPC_DA", "HTTP_GATEWAY"}:
        raise AdapterValidationError(
            "protocol must be one of S7, OPC_UA, OPC_DA, HTTP_GATEWAY"
        )

    if config.get("enabled") is not True:
        return {
            "ready": False,
            "reason": "Live adapter is disabled until plant/OT approval.",
            "protocol": protocol,
            "safety": dict(SAFETY),
        }

    required = ("endpoint", "plant_id")
    missing = [key for key in required if not str(config.get(key) or "").strip()]
    if missing:
        raise AdapterValidationError(
            "missing live configuration: " + ", ".join(missing)
        )

    return {
        "ready": True,
        "protocol": protocol,
        "endpoint": str(config["endpoint"]),
        "plant_id": str(config["plant_id"]),
        "safety": dict(SAFETY),
    }
