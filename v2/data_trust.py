"""Universal V2 data trust and freshness evaluation.

This layer evaluates incoming IndustrialPoint evidence only. It does not
perform prediction, diagnosis, alarm decisions, authorization, or control.
The policy is plant-neutral: plant data/configuration changes, not code.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .contracts import IndustrialPoint


@dataclass(frozen=True)
class DataTrustResult:
    trust: str
    freshness: str
    age_seconds: Optional[float]
    quality: str
    accepted: bool
    reason: str

    def to_dict(self):
        return {
            "trust": self.trust,
            "freshness": self.freshness,
            "age_seconds": self.age_seconds,
            "quality": self.quality,
            "accepted": self.accepted,
            "reason": self.reason,
        }


class DataTrustPolicy:
    """Plant-neutral policy for freshness and source quality checks."""

    def __init__(
        self,
        fresh_after_seconds: float = 10.0,
        stale_after_seconds: float = 60.0,
        reject_after_seconds: float = 300.0,
    ) -> None:
        if not (0 < fresh_after_seconds <= stale_after_seconds <= reject_after_seconds):
            raise ValueError("fresh_after_seconds <= stale_after_seconds <= reject_after_seconds is required")
        self.fresh_after_seconds = float(fresh_after_seconds)
        self.stale_after_seconds = float(stale_after_seconds)
        self.reject_after_seconds = float(reject_after_seconds)

    @staticmethod
    def _timestamp(value: str) -> Optional[datetime]:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _quality(value: str) -> str:
        quality = str(value or "UNKNOWN").strip().upper()
        return quality if quality in {"GOOD", "DEGRADED", "BAD", "UNKNOWN"} else "UNKNOWN"

    def evaluate(
        self,
        point: IndustrialPoint,
        now: Optional[datetime] = None,
    ) -> DataTrustResult:
        parsed = self._timestamp(point.timestamp)
        quality = self._quality(point.quality)

        if parsed is None:
            return DataTrustResult(
                trust="UNTRUSTED",
                freshness="INVALID",
                age_seconds=None,
                quality=quality,
                accepted=False,
                reason="invalid_or_missing_timestamp",
            )

        current = (now or datetime.now(timezone.utc))
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        current = current.astimezone(timezone.utc)
        age = (current - parsed).total_seconds()

        if age < 0:
            freshness = "FUTURE"
            accepted = False
            reason = "timestamp_in_future"
        elif age > self.reject_after_seconds:
            freshness = "EXPIRED"
            accepted = False
            reason = "data_too_old"
        elif age > self.stale_after_seconds:
            freshness = "STALE"
            accepted = True
            reason = "data_stale_but_retained_for_context"
        elif age > self.fresh_after_seconds:
            freshness = "AGING"
            accepted = True
            reason = "data_aging"
        else:
            freshness = "FRESH"
            accepted = True
            reason = "fresh_data"

        if quality == "BAD":
            trust = "UNTRUSTED"
            accepted = False
            reason = "source_quality_bad"
        elif quality == "DEGRADED":
            trust = "DEGRADED"
            reason = reason if accepted else reason
        elif quality == "UNKNOWN":
            trust = "LIMITED"
            reason = "source_quality_unknown" if accepted else reason
        else:
            trust = "TRUSTED" if accepted else "UNTRUSTED"

        return DataTrustResult(
            trust=trust,
            freshness=freshness,
            age_seconds=round(max(age, 0.0), 3),
            quality=quality,
            accepted=accepted,
            reason=reason,
        )

    def evaluate_many(self, points, now: Optional[datetime] = None):
        return [self.evaluate(point, now=now) for point in points]
