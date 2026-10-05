from datetime import datetime, timezone, timedelta
import pytest
from anvi_v2_timeseries_contract import TimeSeriesPoint, TimeSeriesStore

def p(org="o1", plant="p1", tag="PT_303", ts=None):
    return TimeSeriesPoint(org, plant, tag, ts or datetime(2026,1,1,tzinfo=timezone.utc), 42.0, "bar", "GOOD", "S7", 1)

def test_append_deduplicates_and_queries():
    s = TimeSeriesStore(); x = p()
    assert s.append(x, "o1", "p1") is True
    assert s.append(x, "o1", "p1") is False
    assert [q.tag for q in s.query("o1","p1",datetime(2025,12,31,tzinfo=timezone.utc),datetime(2026,1,2,tzinfo=timezone.utc))] == ["PT_303"]

def test_foreign_tenant_blocked():
    with pytest.raises(PermissionError):
        TimeSeriesStore().append(p(org="other"), "o1", "p1")

def test_timestamp_quality_and_window_fail_closed():
    with pytest.raises(ValueError): TimeSeriesPoint("o","p","x",datetime(2026,1,1),1).validate()
    with pytest.raises(ValueError): TimeSeriesPoint("o","p","x",datetime(2026,1,1,tzinfo=timezone.utc),1,quality="INVALID").validate()
    s=TimeSeriesStore()
    with pytest.raises(ValueError):
        s.query("o","p",datetime(2026,1,1,tzinfo=timezone.utc),datetime(2026,2,2,tzinfo=timezone.utc))

def test_safety_contract():
    assert TimeSeriesStore().snapshot() == {"points":0,"append_only":True,"read_only":True,"plc_write":False,"scada_control":False,"automatic_execution":False,"human_decision_required":True}
