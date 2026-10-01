import json
import struct

from anvi_edge_agent import EdgeAgent, EdgeAgentConfig
from anvi_edge_runtime import EdgeRuntime, build_tags, load_s7_config
from anvi_edge_spool import EdgeSpool
from anvi_edge_gateway import GatewayConfig, ReadOnlyGateway
from anvi_s7_readonly import SiemensS7ReadOnlyAdapter


class FakeClient:
    def __init__(self, fail=False):
        self.fail = fail
        self.connected = False

    def connect(self, ip, rack, slot):
        if self.fail:
            raise ConnectionError("PLC offline")
        self.connected = True

    def disconnect(self):
        self.connected = False

    def db_read(self, db, start, size):
        return struct.pack(">f", 42.5)


def test_runtime_config_is_data_driven(tmp_path):
    p = tmp_path / "s7.json"
    p.write_text(json.dumps({
        "plc": {"ip": "10.0.0.1", "rack": 0, "slot": 1},
        "tags": [{"tag": "PT-303", "area": "DB", "db_number": 1, "byte_offset": 0, "data_type": "REAL"}]
    }))
    cfg = load_s7_config(str(p))
    assert build_tags(cfg)[0].tag == "PT-303"


def test_runtime_spools_when_cloud_is_unavailable(tmp_path):
    agent = EdgeAgent(EdgeAgentConfig("P1", "GW1", cloud_url="https://127.0.0.1:1"))
    spool = EdgeSpool(str(tmp_path / "spool.db"), max_batches=2, max_bytes=10000)
    runtime = EdgeRuntime(agent, spool, None, build_tags({
        "tags": [{"tag": "PT-303", "data_type": "REAL"}]
    }), interval_s=1)
    result = runtime.collect_once()
    assert result["queued"] is True
    assert spool.status()["queued_batches"] == 1


def test_runtime_s7_failure_is_safe(tmp_path):
    gateway = ReadOnlyGateway(GatewayConfig("P1", "GW1", source="SIEMENS_S7", protocol="SIEMENS_S7"))
    adapter = SiemensS7ReadOnlyAdapter(gateway, "10.0.0.1", snap7_client=FakeClient(fail=True))
    runtime = EdgeRuntime(
        EdgeAgent(EdgeAgentConfig("P1", "GW1")),
        EdgeSpool(str(tmp_path / "spool.db")),
        adapter,
        build_tags({"tags": [{"tag": "PT-303", "area": "DB", "db_number": 1, "byte_offset": 0, "data_type": "REAL"}]}),
    )
    result = runtime.run_cycle()
    assert result["status"] == "ERROR"
    assert result["safety"]["plc_write"] is False
    assert adapter.status()["status"] == "DISCONNECTED"
