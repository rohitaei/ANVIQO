"""Tests for the ANVIQO V2 read-only edge gateway foundation."""

from anvi_edge_gateway import GatewayConfig, ReadOnlyGateway, SiemensS7Adapter, SAFETY


def test_normalization_and_safety():
    gw = ReadOnlyGateway(GatewayConfig("P1", "GW1"))
    item = gw.normalize("PT-303", 43.2, quality="good")
    assert item["plant_id"] == "P1"
    assert item["gateway_id"] == "GW1"
    assert item["tag"] == "PT-303"
    assert item["quality"] == "GOOD"


def test_ingest_accepts_valid_and_rejects_invalid():
    gw = ReadOnlyGateway(GatewayConfig("P1", "GW1"))
    result = gw.ingest([
        {"tag": "PT-303", "value": 43.2},
        {"tag": "PT-402", "value": 51.1},
        {"tag": "", "value": 10},
    ])
    assert result["accepted"] == 2
    assert result["rejected"] == 1
    assert result["safety"] == SAFETY


def test_gateway_cannot_enable_write():
    try:
        ReadOnlyGateway(GatewayConfig("P1", "GW1", plc_write_enabled=True))
    except ValueError:
        pass
    else:
        raise AssertionError("PLC write must be rejected")


def test_siemens_adapter_stays_disabled():
    gw = ReadOnlyGateway(GatewayConfig("P1", "GW1"))
    adapter = SiemensS7Adapter(gw)
    assert adapter.enabled is False
    assert adapter.status()["status"] == "DISABLED"
    assert adapter.status()["plc_write"] is False
    try:
        adapter.connect()
    except RuntimeError:
        pass
    else:
        raise AssertionError("Live S7 connection must remain disabled")


def test_health_is_read_only():
    gw = ReadOnlyGateway(GatewayConfig("P1", "GW1"))
    health = gw.health()
    assert health["status"] == "READY"
    assert health["read_only"] is True
    assert health["plc_write"] is False
    assert health["scada_control"] is False
