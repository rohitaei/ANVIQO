"""ANVIQO V2 read-only telemetry adapter registry.

This is a protocol-neutral registry and validation layer. It does not connect to
or write to PLC/SCADA systems. Real protocol drivers must implement this contract
and pass certification before production use.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

from anvi_global_v2_contracts import SUPPORTED_PROTOCOLS, SAFETY, normalize_observation

@dataclass(frozen=True)
class ConnectorSpec:
    protocol: str
    mode: str = "READ_ONLY"
    direction: str = "OUTBOUND_ONLY"
    buffering: bool = True
    quality_required: bool = True

REGISTRY = {
    p: ConnectorSpec(protocol=p)
    for p in sorted(SUPPORTED_PROTOCOLS)
    if p not in {"FILE", "API"}
}

_DRIVERS: dict[str, Callable[..., Any]] = {}

def register_driver(protocol: str, driver: Callable[..., Any]) -> None:
    protocol = str(protocol).upper()
    if protocol not in REGISTRY:
        raise ValueError("UNSUPPORTED_PROTOCOL")
    _DRIVERS[protocol] = driver

def registry_status() -> dict[str, Any]:
    return {
        "connectors": {
            p: {
                "registered_driver": p in _DRIVERS,
                "mode": spec.mode,
                "direction": spec.direction,
                "buffering": spec.buffering,
                "quality_required": spec.quality_required,
            }
            for p, spec in REGISTRY.items()
        },
        "safety": dict(SAFETY),
        "note": "Registry presence is not production certification.",
    }

def ingest(protocol: str, observation: dict[str, Any]) -> dict[str, Any]:
    protocol = str(protocol).upper()
    if protocol not in REGISTRY:
        return {"accepted": False, "reason": "UNSUPPORTED_PROTOCOL", "safety": dict(SAFETY)}
    observation = dict(observation)
    observation["source_protocol"] = protocol
    checked = normalize_observation(**observation)
    if not checked["valid"]:
        return {"accepted": False, "reason": "INVALID_OBSERVATION", "validation": checked, "safety": dict(SAFETY)}
    return {"accepted": True, "observation": checked["observation"], "safety": dict(SAFETY)}

def driver_status(protocol: str) -> dict[str, Any]:
    p = str(protocol).upper()
    return {
        "protocol": p,
        "supported": p in REGISTRY,
        "driver_registered": p in _DRIVERS,
        "production_certified": False,
        "write_capability": False,
        "safety": dict(SAFETY),
    }
