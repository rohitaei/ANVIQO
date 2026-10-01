"""ANVIQO V2 Read-Only Plant Edge Gateway contract.

The gateway is the boundary between plant OT data sources and ANVIQO Cloud.
It normalizes observations into one evidence envelope and explicitly blocks
PLC writes and SCADA control.

This module deliberately does NOT open a PLC connection. A vendor/protocol
adapter can be added later behind the same interface after OT approval.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "human_decision_required": True,
    "automatic_authorization": False,
    "automatic_execution": False,
}


@dataclass(frozen=True)
class GatewayConfig:
    plant_id: str
    gateway_id: str
    source: str = "SIMULATION"
    protocol: str = "ADAPTER_CONTRACT"
    update_interval_s: float = 2.0
    outbound_tls_required: bool = True
    plc_write_enabled: bool = False
    scada_control_enabled: bool = False


@dataclass(frozen=True)
class Observation:
    plant_id: str
    gateway_id: str
    tag: str
    value: Any
    timestamp: str
    quality: str = "GOOD"
    source: str = "SIMULATION"
    protocol: str = "ADAPTER_CONTRACT"


class ReadOnlyGateway:
    """Normalize plant observations; never write to PLC/SCADA."""

    def __init__(self, config: GatewayConfig):
        if config.plc_write_enabled or config.scada_control_enabled:
            raise ValueError("ANVIQO gateway is permanently read-only")
        self.config = config

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def normalize(self, tag: str, value: Any, *, timestamp: Optional[str] = None,
                  quality: str = "GOOD", source: Optional[str] = None,
                  protocol: Optional[str] = None) -> Dict[str, Any]:
        if not str(tag).strip():
            raise ValueError("tag is required")
        obs = Observation(
            plant_id=self.config.plant_id,
            gateway_id=self.config.gateway_id,
            tag=str(tag).strip(),
            value=value,
            timestamp=timestamp or self.utc_now(),
            quality=str(quality or "UNKNOWN").upper(),
            source=source or self.config.source,
            protocol=protocol or self.config.protocol,
        )
        return asdict(obs)

    def ingest(self, records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        observations: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        for record in records:
            try:
                observations.append(self.normalize(
                    record.get("tag"),
                    record.get("value"),
                    timestamp=record.get("timestamp"),
                    quality=record.get("quality", "GOOD"),
                    source=record.get("source"),
                    protocol=record.get("protocol"),
                ))
            except Exception as exc:
                rejected.append({"record": dict(record), "reason": str(exc)})
        return {
            "status": "OK" if not rejected else "PARTIAL",
            "gateway": asdict(self.config),
            "observations": observations,
            "accepted": len(observations),
            "rejected": len(rejected),
            "rejected_records": rejected,
            "safety": SAFETY,
        }

    def health(self) -> Dict[str, Any]:
        return {
            "status": "READY",
            "gateway_id": self.config.gateway_id,
            "plant_id": self.config.plant_id,
            "source": self.config.source,
            "protocol": self.config.protocol,
            "outbound_tls_required": self.config.outbound_tls_required,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "safety": SAFETY,
        }


class SiemensS7Adapter:
    """Future adapter contract; intentionally disabled until OT approval."""

    protocol = "SIEMENS_S7"

    def __init__(self, gateway: ReadOnlyGateway):
        self.gateway = gateway
        self.enabled = False

    def status(self) -> Dict[str, Any]:
        return {
            "status": "DISABLED",
            "reason": "LIVE PLC adapter requires OT approval and plant-side configuration",
            "protocol": self.protocol,
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "safety": SAFETY,
        }

    def connect(self, *args, **kwargs):
        raise RuntimeError(
            "Live Siemens S7 connection is disabled. "
            "Configure and approve the plant-side adapter before enabling it."
        )


def simulation_gateway(plant_id: str = "SIMULATION", gateway_id: str = "ANVI-SIM-GW",
                       records: Optional[Iterable[Dict[str, Any]]] = None) -> Dict[str, Any]:
    gateway = ReadOnlyGateway(GatewayConfig(
        plant_id=plant_id,
        gateway_id=gateway_id,
        source="ANVIQO_SIMULATION",
        protocol="SIMULATION_ADAPTER",
    ))
    return gateway.ingest(records or [])


def self_test() -> Dict[str, Any]:
    gateway = ReadOnlyGateway(GatewayConfig(
        plant_id="SIMULATION",
        gateway_id="ANVI-SIM-GW",
    ))
    result = gateway.ingest([
        {"tag": "PT-303", "value": 43.2, "quality": "GOOD"},
        {"tag": "PT-402", "value": 51.1, "quality": "GOOD"},
        {"tag": "", "value": 10},
    ])
    assert result["accepted"] == 2
    assert result["rejected"] == 1
    assert result["safety"] == SAFETY
    adapter = SiemensS7Adapter(gateway)
    assert adapter.enabled is False
    assert adapter.status()["plc_write"] is False
    try:
        adapter.connect()
    except RuntimeError:
        pass
    else:
        raise AssertionError("S7 adapter must remain disabled")
    return {"status": "PASS", "accepted": result["accepted"], "rejected": result["rejected"]}


if __name__ == "__main__":
    print(self_test())
