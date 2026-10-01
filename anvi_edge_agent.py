"""ANVIQO plant-side edge agent.

Runs beside the OT network. It accepts normalized observations from an
approved adapter, enforces the read-only boundary, batches evidence, and
optionally sends HTTPS payloads to an ANVIQO cloud endpoint.

No PLC/SCADA write API exists in this module.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from anvi_edge_gateway import GatewayConfig, ReadOnlyGateway, SAFETY, SiemensS7Adapter


@dataclass(frozen=True)
class EdgeAgentConfig:
    plant_id: str
    gateway_id: str
    cloud_url: str = ""
    api_token: str = ""
    batch_size: int = 100
    outbound_tls_required: bool = True
    mode: str = "SIMULATION"

    @classmethod
    def from_env(cls) -> "EdgeAgentConfig":
        mode = os.getenv("ANVI_EDGE_MODE", "SIMULATION").strip().upper()
        if mode not in {"SIMULATION", "S7_READ_ONLY"}:
            raise ValueError("ANVI_EDGE_MODE must be SIMULATION or S7_READ_ONLY")
        return cls(
            plant_id=os.getenv("ANVI_PLANT_ID", "SIMULATION").strip(),
            gateway_id=os.getenv("ANVI_GATEWAY_ID", "ANVI-EDGE-01").strip(),
            cloud_url=os.getenv("ANVI_CLOUD_URL", "").strip(),
            api_token=os.getenv("ANVI_EDGE_TOKEN", "").strip(),
            batch_size=max(1, int(os.getenv("ANVI_EDGE_BATCH_SIZE", "100"))),
            outbound_tls_required=os.getenv("ANVI_OUTBOUND_TLS", "true").lower() != "false",
            mode=mode,
        )


class EdgeAgent:
    def __init__(self, config: EdgeAgentConfig):
        if config.outbound_tls_required and config.cloud_url and not config.cloud_url.lower().startswith("https://"):
            raise ValueError("ANVI cloud endpoint must use HTTPS")
        self.config = config
        self.gateway = ReadOnlyGateway(GatewayConfig(
            plant_id=config.plant_id,
            gateway_id=config.gateway_id,
            source="ANVIQO_EDGE",
            protocol="SIEMENS_S7" if config.mode == "S7_READ_ONLY" else "SIMULATION_ADAPTER",
            outbound_tls_required=config.outbound_tls_required,
        ))
        self.s7 = SiemensS7Adapter(self.gateway)

    def status(self) -> Dict[str, Any]:
        return {
            "status": "READY",
            "mode": self.config.mode,
            "plant_id": self.config.plant_id,
            "gateway_id": self.config.gateway_id,
            "cloud_configured": bool(self.config.cloud_url),
            "cloud_tls": self.config.cloud_url.startswith("https://") if self.config.cloud_url else None,
            "s7": self.s7.status(),
            "safety": SAFETY,
        }

    def batch(self, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = self.gateway.ingest(records)
        return [result["observations"][i:i + self.config.batch_size]
                for i in range(0, len(result["observations"]), self.config.batch_size)]

    def post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.config.cloud_url:
            return {"status": "NOT_SENT", "reason": "ANVI_CLOUD_URL is not configured"}
        if self.config.outbound_tls_required and not self.config.cloud_url.startswith("https://"):
            raise ValueError("TLS is required for outbound ANVIQO traffic")
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "X-ANVIQO-Gateway": self.config.gateway_id}
        if self.config.api_token:
            headers["Authorization"] = "Bearer " + self.config.api_token
        req = urllib.request.Request(self.config.cloud_url, data=body, headers=headers, method="POST")
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            return {"status": "SENT", "http_status": response.status}

    def run_once(self, records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        raw = list(records)
        batches = self.batch(raw)
        return {
            "status": "READY",
            "input_records": len(raw),
            "batches": len(batches),
            "observations": sum(len(b) for b in batches),
            "safety": SAFETY,
            "cloud": "CONFIGURED" if self.config.cloud_url else "NOT_CONFIGURED",
        }


def self_test() -> Dict[str, Any]:
    cfg = EdgeAgentConfig(plant_id="SIMULATION", gateway_id="ANVI-EDGE-TEST")
    agent = EdgeAgent(cfg)
    result = agent.run_once([
        {"tag": "PT-303", "value": 43.2, "quality": "GOOD"},
        {"tag": "PT-402", "value": 51.1, "quality": "GOOD"},
    ])
    assert result["status"] == "READY"
    assert result["observations"] == 2
    assert agent.status()["safety"] == SAFETY
    assert agent.s7.enabled is False
    return {"status": "PASS", **result}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
