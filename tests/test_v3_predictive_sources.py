from failure_prediction import build_tenant_failure_prediction
from v3.existing_predictor_adapter import make_existing_predictor
from v3.predictive_sources import TenantPredictiveSources, fetch


def _sources():
    def pci(*, plant_id, tag):
        return (
            {"plant_id": plant_id, "tag": tag, "description": "PT"},
            {"plant_id": plant_id, "tag": tag, "value": 120.0, "timestamp": "2026-01-02T00:00:00Z", "state": "HEALTHY"},
        )

    def history(*, plant_id, tag):
        return [
            {"plant_id": plant_id, "tag": tag, "timestamp": "2026-01-01T00:00:00Z", "value": 100.0},
            {"plant_id": plant_id, "tag": tag, "timestamp": "2026-01-02T00:00:00Z", "value": 120.0},
        ]

    def memory(*, plant_id, tag):
        return []

    def events(*, plant_id, tag):
        return []

    def health(*, plant_id, tag):
        return {"plant_id": plant_id, "tag": tag, "status": "HEALTHY"}

    return TenantPredictiveSources(pci, history, memory, events, health)


def test_alpha12_existing_predictor_preserves_existing_trend_logic():
    sources = _sources()
    result = build_tenant_failure_prediction("plant-a", "predict PT-303", "PT-303", sources=sources)
    assert result["plant_id"] == "plant-a"
    assert result["status"] == "PREDICTION_AVAILABLE"
    assert result["risk_signal"] == "TREND_RISING"
    assert result["trend"]["observations_used"] == 2
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False


def test_alpha12_adapter_is_tenant_aware():
    predictor = make_existing_predictor(_sources())
    result = predictor(plant_id="plant-b", tag="PT-303", evidence=[{"plant_id": "plant-b", "tag": "PT-303"}])
    assert result["plant_id"] == "plant-b"
    assert result["tag"] == "PT-303"


def test_alpha12_cross_plant_source_is_rejected():
    sources = _sources()

    def bad_history(*, plant_id, tag):
        return [{"plant_id": "other-plant", "tag": tag, "timestamp": "2026-01-01T00:00:00Z", "value": 100.0}]

    sources = TenantPredictiveSources(
        sources.pci, bad_history, sources.memory, sources.events, sources.health
    )

    try:
        fetch(sources, "plant-a", "PT-303")
    except ValueError as exc:
        assert "cross-plant" in str(exc)
    else:
        raise AssertionError("cross-plant predictive evidence must be rejected")


def test_alpha12_legacy_provider_without_plant_id_is_rejected():
    def legacy(*, tag):
        return []

    try:
        TenantPredictiveSources(legacy, legacy, legacy, legacy, legacy)
        from v3.predictive_sources import validate_sources
        validate_sources(TenantPredictiveSources(legacy, legacy, legacy, legacy, legacy))
    except ValueError as exc:
        assert "plant_id" in str(exc)
    else:
        raise AssertionError("legacy/global source must be rejected")
