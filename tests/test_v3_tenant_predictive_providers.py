from v3.tenant_predictive_providers import TenantPredictiveProviderSet
from v3.predictive_sources import fetch


def _package(plant_id="plant-a"):
    return {
        "plant": {"plant_id": plant_id},
        "records": [
            {
                "record_type": "INSTRUMENT",
                "external_id": "PT-303",
                "tag": "PT-303",
                "name": "Mill outlet pressure",
                "metadata": {
                    "predictive_history": [
                        {"plant_id": plant_id, "tag": "PT-303", "timestamp": "2026-01-01T00:00:00Z", "value": 100.0},
                        {"plant_id": plant_id, "tag": "PT-303", "timestamp": "2026-01-02T00:00:00Z", "value": 120.0},
                    ],
                    "maintenance_memory": [
                        {"plant_id": plant_id, "tag": "PT-303", "timestamp": "2026-01-03T00:00:00Z", "event": "transmitter replaced"}
                    ],
                    "events": [
                        {"plant_id": plant_id, "tag": "PT-303", "timestamp": "2026-01-04T00:00:00Z", "event_type": "WARNING", "message": "pressure changed"}
                    ],
                    "equipment_health": {
                        "plant_id": plant_id,
                        "tag": "PT-303",
                        "status": "WATCH",
                    },
                },
            }
        ],
    }


def test_alpha13_provider_reads_real_onboarding_package_scope():
    provider = TenantPredictiveProviderSet(_package("plant-a"))
    scoped = fetch(provider.sources(), "plant-a", "PT-303")
    assert len(scoped["history"]) == 2
    assert len(scoped["memory"]) == 1
    assert len(scoped["events"]) == 1
    assert scoped["health"]["status"] == "WATCH"
    assert all(row["plant_id"] == "plant-a" for row in scoped["history"])
    assert scoped["safety"]["plc_write"] is False


def test_alpha13_provider_rejects_other_plant():
    provider = TenantPredictiveProviderSet(_package("plant-a"))
    try:
        fetch(provider.sources(), "plant-b", "PT-303")
    except ValueError as exc:
        assert "different plant_id" in str(exc)
    else:
        raise AssertionError("cross-plant provider access must be rejected")


def test_alpha13_provider_rejects_evidence_without_explicit_plant_id():
    package = _package("plant-a")
    package["records"][0]["metadata"]["predictive_history"][0].pop("plant_id")
    provider = TenantPredictiveProviderSet(package)
    try:
        fetch(provider.sources(), "plant-a", "PT-303")
    except ValueError as exc:
        assert "must carry plant_id" in str(exc)
    else:
        raise AssertionError("evidence without explicit plant_id must be rejected")


def test_alpha13_does_not_use_legacy_global_stores():
    provider = TenantPredictiveProviderSet(_package("plant-a"))
    sources = provider.sources()
    assert sources.history(plant_id="plant-a", tag="PT-999") == []
    assert sources.memory(plant_id="plant-a", tag="PT-999") == []
    assert sources.events(plant_id="plant-a", tag="PT-999") == []
