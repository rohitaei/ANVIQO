"""ANVIQO Failure Prediction Demo Integration V1.

Explicitly simulation-only. This module never writes production prediction
history and never connects to PLC/SCADA control paths.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from failure_prediction_demo_loader import load_demo_telemetry, summarize_demo_trend

VERSION = "ANVIQO-FP-DEMO-PREDICTION-V1.0"
DEMO_CSV = Path(__file__).resolve().parent / "database" / "failure_prediction" / "demo" / "pt303_demo_telemetry.csv"

SAFETY = {
    "mode": "DEMO_SIMULATION_ONLY",
    "production_history_write": False,
    "plc_write": False,
    "scada_control": False,
    "automatic_execution": False,
    "human_decision_required": True,
}


def is_demo_failure_prediction_query(question: str) -> bool:
    text = str(question or "").lower()
    demo = any(word in text for word in ("demo", "simulation", "simulated", "synthetic"))
    prediction = any(word in text for word in ("predict", "prediction", "failure", "trend"))
    return demo and prediction


def build_demo_failure_prediction(tag: str = "PT-303") -> Dict[str, Any]:
    """Build a prediction-style demonstration from the fixed synthetic dataset."""
    loaded = load_demo_telemetry(DEMO_CSV)
    observations = [row for row in loaded["observations"] if row["tag"].replace("-", "") == tag.upper().replace("-", "")]
    if not observations:
        return {
            "version": VERSION,
            "status": "NO_DEMO_DATA",
            "tag": tag.upper(),
            "simulation": True,
            "safety": dict(SAFETY),
            "decision_status": "HUMAN_DECISION_REQUIRED",
        }

    trend = summarize_demo_trend(observations)
    return {
        "version": VERSION,
        "status": "DEMO_PREDICTION_AVAILABLE" if trend["status"] == "DEMO_TREND_AVAILABLE" else trend["status"],
        "tag": observations[0]["tag"],
        "source": "SIMULATION",
        "provenance": observations[0]["provenance"],
        "observations": trend.get("observations_used", len(observations)),
        "first_value": trend.get("first", {}).get("value"),
        "last_value": trend.get("last", {}).get("value"),
        "unit": observations[0].get("unit"),
        "delta": trend.get("delta"),
        "direction": trend.get("direction"),
        "prediction": trend.get("prediction"),
        "failure_probability": None,
        "failure_date": None,
        "simulation": True,
        "production_history_write": False,
        "safety": dict(SAFETY),
        "decision_status": "HUMAN_DECISION_REQUIRED",
        "evidence": {
            "dataset": str(DEMO_CSV.relative_to(Path(__file__).resolve().parent)),
            "rows_loaded": loaded["rows_loaded"],
            "historical_observations_used": len(observations),
        },
    }


def demo_answer(question: str) -> Dict[str, Any] | None:
    if not is_demo_failure_prediction_query(question):
        return None
    result = build_demo_failure_prediction()
    return {
        "answer": result.get("prediction") or "No synthetic demo prediction is available.",
        "domain": "failure_prediction_demo",
        "failure_prediction_demo": result,
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "human_decision_required": True,
    }
