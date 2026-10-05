from datetime import datetime, timezone, timedelta

import pytest

from anvi_v2_realtime_store import (
    InMemoryRealtimeStore,
    StreamEvent,
    TelemetryPoint,
)


def ts(seconds=0):
    return datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def test_point_is_append_only_and_deduplicated():
    store = InMemoryRealtimeStore()
    p = TelemetryPoint("org-a", "plant-a", "PT_303", ts(), 42.0, "bar", source="S7")
    first = store.append_point(p)
    second = store.append_point(p)
    assert first == second
    assert len(store.query_points("org-a", "plant-a")) == 1


def test_tenant_boundary_is_query_scoped():
    store = InMemoryRealtimeStore()
    store.append_point(TelemetryPoint("org-a", "plant-a", "PT_303", ts(), 42))
    store.append_point(TelemetryPoint("org-b", "plant-b", "PT_303", ts(), 99))
    assert [p.value for p in store.query_points("org-a", "plant-a")] == [42]
    assert store.query_points("org-a", "plant-b") == []


def test_event_normalization_and_deduplication():
    store = InMemoryRealtimeStore()
    e = StreamEvent("org-a", "plant-a", "alarm", ts(), "High pressure", tag="PT_303")
    first = store.append_event(e)
    second = store.append_event(e)
    assert first == second
    rows = store.query_events("org-a", "plant-a")
    assert len(rows) == 1
    assert rows[0].event_type == "ALARM"


def test_unknown_event_type_fails_closed():
    with pytest.raises(ValueError):
        StreamEvent("org-a", "plant-a", "CAUSE", ts(), "unsupported").normalized()


def test_naive_timestamp_is_rejected():
    with pytest.raises(ValueError):
        TelemetryPoint("org-a", "plant-a", "PT_303", datetime(2026, 10, 5), 42).observation_id


def test_safety_contract_has_no_control_path():
    snapshot = InMemoryRealtimeStore().snapshot()
    assert snapshot["write_capability"] is False
    assert snapshot["plc_write"] is False
    assert snapshot["scada_control"] is False
