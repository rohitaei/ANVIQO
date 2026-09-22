"""Universal predictive-maintenance evidence gateway.

This module is orchestration/evidence gating only. It does not implement a
second prediction engine. A caller may inject the existing prediction
intelligence after tenant-scoped evidence has been validated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from v3.predictive_evidence import validate_prediction_evidence

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


@dataclass(frozen=True)
class PredictionEvidence:
    plant_id: str
    tag: str
    observations: tuple[dict[str, Any], ...]
    source: str = "V3_PREDICTIVE_EVIDENCE_GATEWAY"

    def __post_init__(self) -> None:
        if not str(self.plant_id).strip():
            raise ValueError("plant_id is required")
        if not str(self.tag).strip():
            raise ValueError("tag is required")
        validate_prediction_evidence(self.plant_id, self.tag, list(self.observations))

    @property
    def numeric_timestamped_count(self) -> int:
        count = 0
        for row in self.observations:
            if row.get("timestamp") is None:
                continue
            try:
                float(row["value"])
            except (KeyError, TypeError, ValueError):
                continue
            count += 1
        return count


def build_prediction_request(
    plant_id: str,
    tag: str,
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence = PredictionEvidence(plant_id, tag, tuple(observations))
    quality = validate_prediction_evidence(
        evidence.plant_id, evidence.tag, list(evidence.observations)
    )
    count = quality["usable_observation_count"]
    return {
        "plant_id": evidence.plant_id,
        "tag": evidence.tag,
        "status": "READY_FOR_EXISTING_PREDICTOR" if count >= 2 else "INSUFFICIENT_EVIDENCE",
        "numeric_timestamped_observations": count,
        "evidence": quality["evidence"],
        "evidence_quality": quality,
        "reason": (
            "At least two valid timestamped numeric observations are available."
            if count >= 2
            else "At least two valid timestamped numeric observations are required; no future failure is inferred."
        ),
        "safety": dict(SAFETY),
    }


def run_existing_predictor(
    request: dict[str, Any],
    predictor: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """Invoke an existing predictor only after tenant/evidence validation."""
    if not isinstance(request, dict):
        raise ValueError("prediction request must be a dictionary")
    plant_id = request.get("plant_id")
    tag = request.get("tag")
    if not plant_id or not tag:
        raise ValueError("prediction request requires plant_id and tag")
    for row in request.get("evidence", []):
        if isinstance(row, dict) and row.get("plant_id") not in (None, plant_id):
            raise ValueError("cross-plant predictive evidence is not allowed")

    if request.get("status") != "READY_FOR_EXISTING_PREDICTOR":
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": request.get("reason"),
            "safety": dict(SAFETY),
        }

    if predictor is None:
        return {
            "plant_id": plant_id,
            "tag": tag,
            "status": "NOT_INVOKED",
            "reason": "No existing predictor was supplied; V3 will not create replacement prediction logic.",
            "safety": dict(SAFETY),
        }

    result = predictor(plant_id, tag, request["evidence"])
    return {
        "plant_id": plant_id,
        "tag": tag,
        "status": "INVOKED",
        "result": result,
        "safety": dict(SAFETY),
    }
