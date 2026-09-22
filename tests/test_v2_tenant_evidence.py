from v2.tenant_evidence import TenantEvidenceProvider


def package(plant_id, records):
    return {
        "plant": {"plant_id": plant_id, "name": plant_id},
        "records": records,
    }


def test_provider_returns_only_explicit_v5_evidence():
    provider = TenantEvidenceProvider(package("PLANT-A", [
        {
            "external_id": "PT-303",
            "tag": "PT-303",
            "area": "MILL",
            "name": "Mill pressure",
            "metadata": {"health_score": 90, "status": "HEALTHY"},
        },
        {
            "external_id": "LT-1",
            "tag": "LT-1",
            "area": "MILL",
            "name": "Level transmitter",
        },
    ]))

    result = provider("PLANT-A")
    assert len(result) == 1
    assert result[0]["plant_id"] == "PLANT-A"
    assert result[0]["health_score"] == 90
    assert result[0]["status"] == "HEALTHY"
    assert result[0]["equipment"][0]["tag"] == "PT-303"


def test_provider_does_not_invent_health_from_raw_records():
    provider = TenantEvidenceProvider(package("PLANT-A", [
        {"external_id": "PT-303", "tag": "PT-303", "area": "MILL"},
    ]))
    assert provider("PLANT-A") == []


def test_provider_rejects_cross_plant_request():
    provider = TenantEvidenceProvider(package("PLANT-A", []))
    try:
        provider("PLANT-B")
    except ValueError as exc:
        assert "plant_id" in str(exc)
    else:
        raise AssertionError("cross-plant evidence request was accepted")


def test_provider_snapshot_is_read_only():
    provider = TenantEvidenceProvider(package("PLANT-B", []))
    snapshot = provider.snapshot()
    assert snapshot["plant_id"] == "PLANT-B"
    assert snapshot["safety"]["plc_write"] is False
    assert snapshot["safety"]["scada_control"] is False
    assert snapshot["safety"]["human_decision_required"] is True
