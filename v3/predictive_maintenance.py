"""Universal predictive-maintenance evidence gateway.

This module is orchestration/evidence gating only. It does not implement a
second prediction engine. Predictor invocation is delegated to the canonical
tenant-safe bridge so V3 has one predictor invocation path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from v3.predictive_bridge import invoke_existing_predictor
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
        quality = validate_prediction_evidence(
            self.plant_id, self.tag, list(self.observations)
        )
        return quality["usable_observation_count"]


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
    """Compatibility entry point using the canonical tenant-safe bridge."""
    return invoke_existing_predictor(request, predictor)
