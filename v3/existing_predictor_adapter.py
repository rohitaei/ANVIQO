"""Adapter from V3's tenant-safe predictor bridge to existing prediction intelligence.

No prediction logic lives here. The existing failure_prediction algorithm is
invoked only through its tenant-scoped source contract.
"""
from __future__ import annotations

from typing import Any

from failure_prediction import build_tenant_failure_prediction
from v3.predictive_sources import TenantPredictiveSources, validate_sources

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_action": False,
    "human_decision_required": True,
}


def make_existing_predictor(sources: TenantPredictiveSources):
    validate_sources(sources)

    def predictor(*, plant_id: str, tag: str, evidence: list[dict[str, Any]]):
        if not isinstance(evidence, list):
            raise ValueError("evidence must be a list")
        return build_tenant_failure_prediction(
            plant_id,
            f"predict {tag}",
            tag,
            sources=sources,
        )

    return predictor
