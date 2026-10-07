from datetime import datetime, timezone
from anvi_v2_edge_registry import ingest, registry_status

def test_connector_registry_is_read_only():
    status = registry_status()
    assert set(status["connectors"]) == {"MODBUS_TCP", "MQTT", "OPC_UA", "S7", "SPARKPLUG"}
    assert all(v["mode"] == "READ_ONLY" for v in status["connectors"].values())
    assert all(v["direction"] == "OUTBOUND_ONLY" for v in status["connectors"].values())
    assert status["safety"]["plc_write"] is False
    assert status["safety"]["scada_control"] is False

def test_s7_observation_normalization():
    result = ingest("S7", {
        "organization_id": "org-a",
        "plant_id": "plant-a",
        "tag": "PT-303",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "value": 68.0,
        "quality": "GOOD",
        "unit": "bar",
        "source_address": "DB1.DBW10",
    })
    assert result["accepted"] is True
    assert result["observation"]["source_protocol"] == "S7"

def test_unknown_connector_fails_closed():
    result = ingest("UNKNOWN", {})
    assert result["accepted"] is False
    assert result["reason"] == "UNSUPPORTED_PROTOCOL"
