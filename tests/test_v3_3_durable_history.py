from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from anvi_v2_realtime_store import TelemetryPoint
from anvi_v3_2_historical_evidence import historical_assessment
from anvi_v3_3_durable_history import DurableHistoricalStore


def point(org, plant, tag, ts, value, source="TEST", sequence=None):
    return TelemetryPoint(org, plant, tag, ts, value, "", "GOOD", source, sequence)


def test_durable_append_deduplicates_and_survives_reopen(tmp_path: Path):
    db = str(tmp_path / "history.db")
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store = DurableHistoricalStore(db)
    p = point("O1", "P1", "PT-303", t0, 42.0, sequence=1)
    assert store.append(p) is True
    assert store.append(p) is False
    reopened = DurableHistoricalStore(db)
    rows = reopened.query("O1", "P1", "PT-303")
    assert len(rows) == 1
    assert rows[0].value == 42.0


def test_tenant_and_plant_isolation(tmp_path: Path):
    store = DurableHistoricalStore(str(tmp_path / "history.db"))
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store.append(point("O1", "P1", "PT-303", t0, 10.0))
    store.append(point("O1", "P2", "PT-303", t0, 20.0))
    store.append(point("O2", "P1", "PT-303", t0, 30.0))
    assert [p.value for p in store.query("O1", "P1", "PT-303")] == [10.0]
    assert [p.value for p in store.query("O1", "P2", "PT-303")] == [20.0]
    assert [p.value for p in store.query("O2", "P1", "PT-303")] == [30.0]


def test_replay_preserves_order(tmp_path: Path):
    store = DurableHistoricalStore(str(tmp_path / "history.db"))
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(5):
        store.append(point("O1", "P1", "PT-303", t0 + timedelta(minutes=i), float(i)))
    rows = store.query("O1", "P1", "PT-303")
    assert [p.value for p in rows] == [0, 1, 2, 3, 4]


def test_prediction_validation_records_actual_and_error(tmp_path: Path):
    store = DurableHistoricalStore(str(tmp_path / "history.db"))
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(5):
        store.append(point("O1", "P1", "PT-303", t0 + timedelta(minutes=i), 50.0 + i))
    target = t0 + timedelta(minutes=6)
    store.append(point("O1", "P1", "PT-303", target, 56.0))
    pred = store.record_prediction(
        organization_id="O1", plant_id="P1", tag="PT-303",
        target_time=target, predicted_value=55.0,
        model="TEST", evidence_status="READY_FOR_VALIDATION",
        prediction_id="pred-1")
    assert pred["validation_status"] == "PENDING"
    result = store.validate_due(
        organization_id="O1", plant_id="P1", tag="PT-303",
        prediction_id="pred-1", tolerance=1.0)
    assert result["validation_status"] == "VALIDATED"
    assert result["actual_value"] == 56.0
    assert result["absolute_error"] == 1.0
    assert result["safety"]["plc_write"] is False


def test_prediction_cannot_bypass_insufficient_evidence(tmp_path: Path):
    store = DurableHistoricalStore(str(tmp_path / "history.db"))
    with pytest.raises(ValueError, match="PREDICTION_EVIDENCE_INSUFFICIENT"):
        store.record_prediction(
            organization_id="O1", plant_id="P1", tag="PT-303",
            target_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            predicted_value=55.0, model="TEST",
            evidence_status="INSUFFICIENT_HISTORY", prediction_id="blocked")


def test_historical_readiness_remains_evidence_gated():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [point("O1", "P1", "PT-303", t0 + timedelta(seconds=i * 60), 10 + i)
            for i in range(4)]
    result = historical_assessment(rows)
    assert result["prediction_readiness"] == "INSUFFICIENT_HISTORY"
    assert result["safety"]["causation_claim"] is False
