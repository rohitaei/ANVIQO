from datetime import datetime, timedelta, timezone
from anvi_v2_realtime_store import TelemetryPoint
from anvi_v3_2_historical_evidence import historical_assessment

def _rows():
    base = datetime(2026, 10, 7, tzinfo=timezone.utc)
    return [
        TelemetryPoint("o", "p", "PT-303", base + timedelta(seconds=i * 120), 42 + i * 5, source="SIM")
        for i in range(6)
    ]

def test_trend_requires_and_reports_real_history():
    result = historical_assessment(_rows(), min_samples=5, min_span_seconds=300)
    assert result["history_sufficient"] is True
    assert result["direction"] == "INCREASING"
    assert result["prediction_readiness"] == "READY_FOR_VALIDATION"
    assert result["causation_claim"] if "causation_claim" in result else True

def test_short_history_blocks_predictive_claim():
    result = historical_assessment(_rows()[:2], min_samples=5, min_span_seconds=300)
    assert result["history_sufficient"] is False
    assert result["prediction_readiness"] == "INSUFFICIENT_HISTORY"
    assert "more historical evidence" in result["reason"]

def test_empty_history_is_explicit():
    result = historical_assessment([])
    assert result["status"] == "NO_EVIDENCE"
    assert result["history_sufficient"] is False
