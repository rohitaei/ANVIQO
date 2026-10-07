from datetime import datetime, timezone, timedelta

from anvi_v2_realtime_store import InMemoryRealtimeStore, StreamEvent, TelemetryPoint
from anvi_v2_realtime_replay import replay_window


def test_replay_merges_telemetry_and_events_in_time_order():
    store = InMemoryRealtimeStore()
    base = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    store.append_point(TelemetryPoint("o", "p", "PT_303", base, 42, source="S7"))
    store.append_event(StreamEvent("o", "p", "ALARM", base + timedelta(seconds=2), "High pressure", tag="PT_303"))
    store.append_point(TelemetryPoint("o", "p", "PT_303", base + timedelta(seconds=4), 68, source="S7"))
    result = replay_window(store, "o", "p", base, base + timedelta(seconds=5))
    assert result["evidence_count"] == 3
    assert [x["kind"] for x in result["timeline"]] == ["TELEMETRY", "EVENT", "TELEMETRY"]
    assert result["causation_claimed"] is False
    assert result["safety"]["plc_write"] is False


def test_replay_is_tenant_scoped():
    store = InMemoryRealtimeStore()
    base = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    store.append_point(TelemetryPoint("o1", "p1", "PT_303", base, 42))
    store.append_point(TelemetryPoint("o2", "p2", "PT_303", base, 99))
    result = replay_window(store, "o1", "p1", base, base + timedelta(minutes=1))
    assert result["evidence_count"] == 1
    assert result["timeline"][0]["value"] == 42
