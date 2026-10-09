from datetime import datetime, timezone, timedelta
import pytest

from anvi_v4_2_connector_validation import validate_connector_stream, SAFETY

NOW = datetime(2026, 10, 9, 4, 0, tzinfo=timezone.utc)


def source(**updates):
    row = {"source_id": "edge-1", "source_type": "PLC_EDGE",
           "organization_id": "ORG", "plant_id": "PLANT", "read_only": True}
    row.update(updates)
    return row


def obs(tag="PT-303", sequence=1, **updates):
    row = {"source_id": "edge-1", "organization_id": "ORG", "plant_id": "PLANT",
           "tag": tag, "sequence": sequence, "value": 42.0,
           "observed_at": NOW.isoformat()}
    row.update(updates)
    return row


def test_empty_stream_is_unavailable_not_healthy():
    report = validate_connector_stream(source=source(), observations=[], now=NOW)
    assert report["status"] == "UNAVAILABLE"
    assert report["live_connection_verified"] is False


def test_fresh_complete_stream_healthy():
    report = validate_connector_stream(source=source(), observations=[obs()], now=NOW,
                                       expected_tags=["PT-303"])
    assert report["status"] == "HEALTHY"
    assert report["live_connection_verified"] is True
    assert report["last_seen"] is not None


def test_stale_telemetry_is_stale():
    report = validate_connector_stream(
        source=source(),
        observations=[obs(observed_at=(NOW - timedelta(hours=1)).isoformat())],
        now=NOW, stale_after_seconds=300,
    )
    assert report["status"] == "STALE"
    assert report["timestamp_quality"]["stale"] == 1


def test_missing_timezone_is_invalid_timestamp():
    report = validate_connector_stream(source=source(),
        observations=[obs(observed_at="2026-10-09T04:00:00")], now=NOW)
    assert report["timestamp_quality"]["invalid_or_timezone_missing"] == 1
    assert report["status"] == "DEGRADED"


def test_future_timestamp_is_flagged():
    report = validate_connector_stream(source=source(),
        observations=[obs(observed_at=(NOW + timedelta(minutes=5)).isoformat())], now=NOW)
    assert report["timestamp_quality"]["future_beyond_tolerance"] == 1
    assert report["status"] == "DEGRADED"


def test_duplicate_tag_sequence_detected():
    report = validate_connector_stream(source=source(),
        observations=[obs(sequence=10), obs(sequence=10)], now=NOW)
    assert report["data_quality"]["duplicate_observations"] == 1
    assert report["status"] == "DEGRADED"


def test_sequence_gaps_counted():
    report = validate_connector_stream(source=source(),
        observations=[obs(sequence=1), obs(sequence=4)], now=NOW)
    assert report["data_quality"]["sequence_gaps"] == 2
    assert report["status"] == "DEGRADED"


def test_missing_values_and_expected_tags_detected():
    report = validate_connector_stream(source=source(),
        observations=[obs(value=None)], expected_tags=["PT-303", "PT-519"], now=NOW)
    assert report["data_quality"]["missing_values"] == 1
    assert report["data_quality"]["expected_tags_missing"] == ["PT-519"]
    assert report["status"] == "DEGRADED"


def test_tenant_plant_or_source_mismatch_is_scope_violation():
    report = validate_connector_stream(source=source(),
        observations=[obs(plant_id="OTHER")], now=NOW)
    assert report["status"] == "SCOPE_VIOLATION"
    assert report["data_quality"]["scope_violations"] == 1
    assert report["live_connection_verified"] is False


def test_unknown_source_and_write_mode_are_blocked():
    assert validate_connector_stream(source=source(source_type="UNKNOWN"),
        observations=[obs()], now=NOW)["status"] == "UNSUPPORTED"
    assert validate_connector_stream(source=source(read_only=False),
        observations=[obs()], now=NOW)["status"] == "BLOCKED_WRITE_MODE"


def test_invalid_thresholds_rejected():
    with pytest.raises(ValueError, match="TIME_THRESHOLDS"):
        validate_connector_stream(source=source(), observations=[], now=NOW,
                                  stale_after_seconds=-1)
    with pytest.raises(ValueError, match="TIMEZONE_AWARE"):
        validate_connector_stream(source=source(), observations=[], now=datetime(2026, 10, 9))


def test_safety_contract_is_read_only():
    report = validate_connector_stream(source=source(), observations=[obs()], now=NOW)
    assert report["safety"]["plc_write"] is False
    assert report["safety"]["scada_control"] is False
    assert report["safety"]["automatic_execution"] is False
    assert report["safety"]["human_decision_required"] is True
