from datetime import datetime, timezone, timedelta

from anvi_v2_realtime_store import StreamEvent
from anvi_v2_event_correlation import correlate_stream_events


def test_stream_events_feed_existing_generic_correlation():
    base = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    events = [
        StreamEvent("o", "p", "ALARM", base, "Pressure high", tag="PT_303"),
        StreamEvent("o", "p", "STATE_CHANGE", base + timedelta(seconds=5), "State changed", tag="PT_303"),
    ]
    result = correlate_stream_events("PT_303", events)
    assert result["event_count"] == 2
    assert result["source_contract"] == "ANVIQO_V2_STREAM_EVENT"
    assert result["causation_claimed"] is False


def test_foreign_equipment_is_not_mixed():
    base = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    events = [
        StreamEvent("o", "p", "ALARM", base, "PT alarm", tag="PT_303"),
        StreamEvent("o", "p", "ALARM", base, "Other alarm", tag="PT_402"),
    ]
    result = correlate_stream_events("PT_303", events)
    assert result["event_count"] == 1
