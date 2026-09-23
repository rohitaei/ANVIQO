"""Canonical entry point for V3 prediction using a normalized plant package.

This adds wiring only. Prediction logic remains in failure_prediction.py.
"""
from __future__ import annotations

from typing import Any, Mapping

from v3.predictive_flow import run_predictive_flow
from v3.tenant_predictive_providers import TenantPredictiveProviderSet


def run_predictive_flow_from_package(
    plant_id: str,
    tag: str,
    observations: list[dict[str, Any]],
    *,
    package: Mapping[str, Any],
    outcome: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the canonical V3 flow with real tenant-scoped package providers."""
    provider = TenantPredictiveProviderSet(package)
    if provider.plant_id != str(plant_id or "").strip():
        raise ValueError("onboarding package plant_id does not match requested plant_id")

    from v3.existing_predictor_adapter import make_existing_predictor

    sources = provider.sources()
    predictor = make_existing_predictor(sources)
    return run_predictive_flow(
        plant_id,
        tag,
        observations,
        predictor=predictor,
        history_provider=sources.history,
        maintenance_memory_provider=sources.memory,
        outcome=outcome,
    )


__all__ = ["run_predictive_flow_from_package"]
