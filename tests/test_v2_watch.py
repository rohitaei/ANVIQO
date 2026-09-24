from datetime import datetime, timedelta, timezone

from v2.contracts import IndustrialPoint
from v2.data_fabric import ReadOnlyDataFabric
from v2.watch import WatchOrchestrator


def point(tag, value, seconds_ago=0, quality="GOOD"):
    ts = datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)
    return IndustrialPoint(
        plant_id="A",
        tag=tag,
        timestamp=ts.isoformat(),
        value=value,
        source="TEST",
        mode="SIMULATION",
        quality=quality,
    )


def test_watch_is_quiet_on_first_stable_observation():
    fabric = ReadOnlyDataFabric()
    fabric.ingest(point("PT-1", 10))
    result = WatchOrchestrator(fabric).observe("A")
    assert result.state == "OBSERVE"
    assert result.candidates == ()


def test_watch_discovers_generic_value_change_without_calling_it_an_anomaly():
    fabric = ReadOnlyDataFabric()
    runner = WatchOrchestrator(fabric)
    fabric.ingest(point("PT-1", 10))
    runner.observe("A")
    fabric.ingest(point("PT-1", 12))
    result = runner.observe("A")
    assert result.state == "WATCH"
    assert any(
        x.reason == "value_changed_since_previous_observation"
        for x in result.candidates
    )
    assert "does not classify" in result.discovery["meaning"]


def test_watch_preserves_trust_and_tenant_scope():
    fabric = ReadOnlyDataFabric()
    fabric.ingest(point("PT-1", 10, quality="BAD"))
    result = WatchOrchestrator(fabric).observe("A")
    other = WatchOrchestrator(fabric).observe("B")
    assert result.state == "INSUFFICIENT_EVIDENCE"
    assert result.untrusted_points == 1
    assert other.points_seen == 0
    assert result.safety["plc_write"] is False
    assert result.safety["scada_control"] is False


def test_watch_reuses_injected_v5_bridge():
    fabric = ReadOnlyDataFabric()
    fabric.ingest(point("PT-1", 10))
    calls = []

    def bridge(**kwargs):
        calls.append(kwargs)
        return {"status": "delegated"}

    result = WatchOrchestrator(fabric, v5_bridge=bridge).run_once("A")
    assert calls and calls[0]["plant_id"] == "A"
    assert result["discovery"]["v5"]["status"] == "INVOKED"
