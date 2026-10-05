"""V2 tenant-safe prediction/anomaly validation primitives."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class PredictionMetric:
    tenant: object
    model_id: str
    metric: str
    value: float
    measured_at: datetime
    sample_count: int = 0
    def validate(self) -> None:
        if self.measured_at.tzinfo is None: raise ValueError("timestamp must have timezone")
        if not self.model_id or not self.metric: raise ValueError("model and metric are required")
        if self.sample_count < 0: raise ValueError("sample_count must be non-negative")
        if not isinstance(self.value, (int, float)): raise ValueError("metric value must be numeric")

@dataclass(frozen=True)
class AnomalyAssessment:
    tenant: object
    assessment_id: str
    observed_at: datetime
    score: float
    threshold: float
    confidence: float
    evidence_ids: tuple[str, ...] = ()
    def validate(self) -> None:
        if self.observed_at.tzinfo is None: raise ValueError("timestamp must have timezone")
        if not self.assessment_id: raise ValueError("assessment_id is required")
        if not 0.0 <= self.score <= 1.0 or not 0.0 <= self.threshold <= 1.0 or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("scores/confidence must be between 0 and 1")

@dataclass(frozen=True)
class PredictionOutcome:
    tenant: object
    prediction_id: str
    predicted_at: datetime
    evaluated_at: datetime
    predicted_value: float
    actual_value: float
    absolute_error: float
    def validate(self) -> None:
        for ts in (self.predicted_at, self.evaluated_at):
            if ts.tzinfo is None: raise ValueError("timestamp must have timezone")
        if self.evaluated_at < self.predicted_at: raise ValueError("evaluation cannot precede prediction")
        if not self.prediction_id: raise ValueError("prediction_id is required")
        if self.absolute_error < 0: raise ValueError("absolute_error must be non-negative")

def drift_signal(current: float, baseline: float, tolerance: float = 0.0) -> bool:
    if tolerance < 0: raise ValueError("tolerance must be non-negative")
    return abs(current - baseline) > tolerance
