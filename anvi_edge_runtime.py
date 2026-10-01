"""ANVIQO production edge runtime.

One safe plant-side loop:
S7 read-only adapter -> normalized observations -> bounded spool -> HTTPS cloud.
Cloud outages never lose already accepted batches; replay occurs before new
data is uploaded. PLC/SCADA writes are structurally unavailable.
"""

from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from anvi_edge_agent import EdgeAgent, EdgeAgentConfig
from anvi_edge_spool import EdgeSpool
from anvi_s7_readonly import S7Tag, SiemensS7ReadOnlyAdapter
from anvi_edge_gateway import SAFETY, ReadOnlyGateway, GatewayConfig


def _json_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("S7 configuration must be a JSON object")
    return value


def load_s7_config(path: str) -> Dict[str, Any]:
    cfg = _json_file(path)
    plc = cfg.get("plc")
    tags = cfg.get("tags")
    if not isinstance(plc, dict):
        raise ValueError("s7 config requires plc object")
    if not isinstance(tags, list) or not tags:
        raise ValueError("s7 config requires at least one tag")
    return cfg


def build_tags(config: Dict[str, Any]) -> List[S7Tag]:
    result: List[S7Tag] = []
    for raw in config["tags"]:
        if not isinstance(raw, dict):
            raise ValueError("each tag definition must be an object")
        result.append(S7Tag(
            tag=str(raw["tag"]),
            area=str(raw.get("area", "DB")),
            db_number=int(raw.get("db_number", 0)),
            byte_offset=int(raw.get("byte_offset", 0)),
            bit_offset=(None if raw.get("bit_offset") is None else int(raw["bit_offset"])),
            data_type=str(raw.get("data_type", "REAL")),
            length=(None if raw.get("length") is None else int(raw["length"])),
            scale=float(raw.get("scale", 1.0)),
            offset=float(raw.get("offset", 0.0)),
        ))
    return result


class EdgeRuntime:
    def __init__(self, agent: EdgeAgent, spool: EdgeSpool, s7: Optional[SiemensS7ReadOnlyAdapter],
                 tags: Iterable[S7Tag], interval_s: float = 2.0, retry_s: float = 5.0):
        self.agent = agent
        self.spool = spool
        self.s7 = s7
        self.tags = list(tags)
        self.interval_s = max(0.2, float(interval_s))
        self.retry_s = max(0.5, float(retry_s))
        self.running = False
        self.cycles = 0
        self.last_error = None
        self.last_delivery = None

    def status(self) -> Dict[str, Any]:
        return {
            "status": "RUNNING" if self.running else "READY",
            "mode": self.agent.config.mode,
            "plant_id": self.agent.config.plant_id,
            "gateway_id": self.agent.config.gateway_id,
            "cycles": self.cycles,
            "last_error": self.last_error,
            "last_delivery": self.last_delivery,
            "s7": self.s7.status() if self.s7 else {"status": "SIMULATION"},
            "spool": self.spool.status(),
            "safety": SAFETY,
        }

    def _payload(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "plant_id": self.agent.config.plant_id,
            "gateway_id": self.agent.config.gateway_id,
            "observations": observations,
            "safety": SAFETY,
        }

    def _deliver(self, payload: Dict[str, Any]) -> bool:
        try:
            result = self.agent.post(payload)
            if result.get("status") == "SENT":
                self.last_delivery = "SENT"
                return True
            if result.get("status") == "NOT_SENT":
                self.last_delivery = "NOT_CONFIGURED"
                return False
            self.last_delivery = result.get("status", "FAILED")
            return False
        except Exception as exc:
            self.last_error = type(exc).__name__ + ": " + str(exc)
            self.last_delivery = "FAILED"
            return False

    def replay_spool(self, limit: int = 20) -> Dict[str, int]:
        sent = 0
        failed = 0
        for item in self.spool.peek(limit):
            if self._deliver(item["payload"]):
                self.spool.acknowledge(item["id"])
                sent += 1
            else:
                failed += 1
                break
        return {"sent": sent, "failed": failed}

    def collect_once(self) -> Dict[str, Any]:
        self.cycles += 1
        if self.s7 is None:
            # Safe simulation mode; it uses the same normalization path as S7.
            raw = []
            for item in self.tags:
                raw.append({"tag": item.tag, "value": 0.0, "quality": "SIMULATED"})
            observations = self.agent.gateway.ingest(raw)["observations"]
            read_status = "SIMULATION"
        else:
            if not self.s7.status()["status"] == "CONNECTED":
                self.s7.connect()
            result = self.s7.read_many(self.tags)
            observations = result["observations"]
            read_status = result["status"]

        payload = self._payload(observations)
        delivered = self._deliver(payload)
        queued = False
        if not delivered and observations:
            self.spool.enqueue(payload)
            queued = True

        return {
            "status": read_status,
            "observations": len(observations),
            "delivered": delivered,
            "queued": queued,
            "spool": self.spool.status(),
            "safety": SAFETY,
        }

    def run_cycle(self) -> Dict[str, Any]:
        # Oldest evidence is delivered first to preserve chronology.
        replay = self.replay_spool()
        try:
            result = self.collect_once()
            result["replayed"] = replay
            self.last_error = None
            return result
        except Exception as exc:
            self.last_error = type(exc).__name__ + ": " + str(exc)
            # Disconnect so the next cycle performs a clean reconnect.
            if self.s7 is not None:
                try:
                    self.s7.disconnect()
                except Exception:
                    pass
            return {
                "status": "ERROR",
                "error": self.last_error,
                "replayed": replay,
                "spool": self.spool.status(),
                "safety": SAFETY,
            }

    def run_forever(self) -> None:
        self.running = True
        try:
            while self.running:
                self.run_cycle()
                time.sleep(self.interval_s if not self.last_error else self.retry_s)
        finally:
            self.running = False
            if self.s7 is not None:
                self.s7.disconnect()


def build_runtime_from_env() -> EdgeRuntime:
    agent_cfg = EdgeAgentConfig.from_env()
    spool = EdgeSpool(
        os.getenv("ANVI_EDGE_SPOOL", "./anvi_edge_spool.db"),
        max_batches=int(os.getenv("ANVI_EDGE_SPOOL_MAX_BATCHES", "1000")),
        max_bytes=int(os.getenv("ANVI_EDGE_SPOOL_MAX_BYTES", "50000000")),
    )
    mode = agent_cfg.mode
    s7 = None
    if mode == "S7_READ_ONLY":
        config_path = os.getenv("ANVI_S7_CONFIG", "anvi_s7_config.json")
        cfg = load_s7_config(config_path)
        plc = cfg["plc"]
        gateway = agent_cfg and ReadOnlyGateway(GatewayConfig(
            plant_id=agent_cfg.plant_id,
            gateway_id=agent_cfg.gateway_id,
            source="ANVIQO_EDGE",
            protocol="SIEMENS_S7",
            update_interval_s=float(cfg.get("update_interval_s", os.getenv("ANVI_EDGE_LOOP_SECONDS", "2"))),
            outbound_tls_required=agent_cfg.outbound_tls_required,
        ))
        s7 = SiemensS7ReadOnlyAdapter(
            gateway,
            str(plc["ip"]),
            rack=int(plc.get("rack", 0)),
            slot=int(plc.get("slot", 1)),
            timeout_s=float(plc.get("timeout_s", 5)),
        )
        tags = build_tags(cfg)
    else:
        tags = build_tags(_json_file(os.getenv("ANVI_SIM_CONFIG", "anvi_s7_config.example.json")))
    return EdgeRuntime(
        agent,
        spool,
        s7,
        tags,
        interval_s=float(os.getenv("ANVI_EDGE_LOOP_SECONDS", "2")),
        retry_s=float(os.getenv("ANVI_EDGE_RETRY_SECONDS", "5")),
    )


def main() -> None:
    runtime = build_runtime_from_env()
    signal.signal(signal.SIGTERM, lambda *_: setattr(runtime, "running", False))
    signal.signal(signal.SIGINT, lambda *_: setattr(runtime, "running", False))
    print(json.dumps(runtime.status(), indent=2))
    runtime.run_forever()


if __name__ == "__main__":
    main()
