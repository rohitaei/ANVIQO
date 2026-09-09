from pathlib import Path

import pytest

from failure_prediction_demo_loader import load_demo_telemetry, summarize_demo_trend


DEMO = Path(__file__).parent / "database" / "failure_prediction" / "demo" / "pt303_demo_telemetry.csv"


def test_demo_loader_accepts_explicit_simulation_data_without_production_write():
    result = load_demo_telemetry(DEMO)
    assert result["status"] == "DEMO_DATA_LOADED"
    assert result["simulation"] is True
    assert result["production_history_write"] is False
    assert result["rows_loaded"] == 8
    assert all(row["source_type"] == "SIMULATION" for row in result["observations"])


def test_demo_trend_is_rising_and_never_claims_real_failure():
    result = load_demo_telemetry(DEMO)
    trend = summarize_demo_trend(result["observations"])
    assert trend["status"] == "DEMO_TREND_AVAILABLE"
    assert trend["direction"] == "RISING"
    assert trend["first"]["value"] == 48.2
    assert trend["last"]["value"] == 53.7
    assert trend["failure_probability"] is None
    assert trend["failure_date"] is None
    assert trend["simulation"] is True


def test_demo_loader_rejects_non_simulation_rows(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(
        "timestamp,tag,value,unit,quality,source_type,provenance\n"
        "2026-09-09T18:00:00Z,PT-303,48.2,kg/cm²,GOOD,LIVE_TELEMETRY,REAL\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source_type=SIMULATION"):
        load_demo_telemetry(path)
