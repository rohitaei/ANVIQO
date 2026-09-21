from datetime import datetime, timezone, timedelta

from v2.contracts import IndustrialPoint
from v2.data_trust import DataTrustPolicy


def point(timestamp, quality="GOOD"):
    return IndustrialPoint(
        plant_id="plant-a",
        tag="PT-303",
        timestamp=timestamp,
        value=42.5,
        source="UNIVERSAL TEST",
        quality=quality,
    )


def test_fresh_data_is_trusted():
    now = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
    result = DataTrustPolicy().evaluate(
        point("2026-09-21T09:59:55+00:00"),
        now=now,
    )
    assert result.trust == "TRUSTED"
    assert result.freshness == "FRESH"
    assert result.accepted is True


def test_stale_data_is_retained_but_not_fresh():
    now = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
    result = DataTrustPolicy().evaluate(
        point("2026-09-21T09:58:00+00:00"),
        now=now,
    )
    assert result.trust == "TRUSTED"
    assert result.freshness == "STALE"
    assert result.accepted is True


def test_bad_quality_is_not_trusted():
    now = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
    result = DataTrustPolicy().evaluate(
        point("2026-09-21T09:59:55+00:00", quality="BAD"),
        now=now,
    )
    assert result.trust == "UNTRUSTED"
    assert result.accepted is False


def test_invalid_and_future_timestamps_are_rejected():
    policy = DataTrustPolicy()
    now = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
    assert policy.evaluate(point("not-a-time"), now=now).accepted is False
    assert policy.evaluate(
        point((now + timedelta(seconds=1)).isoformat()),
        now=now,
    ).freshness == "FUTURE"


def test_policy_is_plant_neutral():
    now = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
    a = point("2026-09-21T09:59:55+00:00")
    b = IndustrialPoint(**{**a.to_dict(), "plant_id": "cement-plant", "tag": "TEMP-1"})
    assert policy := DataTrustPolicy()
    assert policy.evaluate(a, now=now).to_dict() == policy.evaluate(b, now=now).to_dict()
