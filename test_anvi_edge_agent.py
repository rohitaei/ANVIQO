import os
import pytest

from anvi_edge_agent import EdgeAgent, EdgeAgentConfig


def test_agent_simulation_is_ready_and_read_only():
    agent = EdgeAgent(EdgeAgentConfig("P1", "GW1"))
    result = agent.run_once([{"tag": "PT-303", "value": 42.0}])
    assert result["status"] == "READY"
    assert result["observations"] == 1
    assert agent.status()["safety"]["plc_write"] is False
    assert agent.status()["safety"]["scada_control"] is False


def test_agent_rejects_non_tls_cloud():
    with pytest.raises(ValueError, match="HTTPS"):
        EdgeAgent(EdgeAgentConfig("P1", "GW1", cloud_url="http://example.invalid"))


def test_s7_mode_remains_disabled():
    agent = EdgeAgent(EdgeAgentConfig("P1", "GW1", mode="S7_READ_ONLY"))
    assert agent.s7.status()["status"] == "DISABLED"
    with pytest.raises(RuntimeError):
        agent.s7.connect()
