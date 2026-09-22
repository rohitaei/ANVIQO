from v3.maintenance_memory_bridge import fetch_tenant_maintenance_memory


def test_legacy_global_memory_provider_is_blocked():
    def legacy(tag):
        return [{"tag": tag}]

    result = fetch_tenant_maintenance_memory("PLANT-A", "PT-303", legacy)
    assert result["status"] == "NOT_INVOKED"
    assert "legacy/global" in result["reason"]


def test_tenant_aware_memory_provider_is_invoked():
    seen = {}

    def provider(*, plant_id, tag):
        seen.update(plant_id=plant_id, tag=tag)
        return [{"plant_id": plant_id, "tag": tag, "verified": True}]

    result = fetch_tenant_maintenance_memory("PLANT-A", "PT-303", provider)
    assert result["status"] == "INVOKED"
    assert result["record_count"] == 1
    assert seen == {"plant_id": "PLANT-A", "tag": "PT-303"}


def test_cross_plant_memory_is_rejected():
    def provider(*, plant_id, tag):
        return [{"plant_id": "PLANT-B", "tag": tag}]

    try:
        fetch_tenant_maintenance_memory("PLANT-A", "PT-303", provider)
    except ValueError as exc:
        assert "plant scope" in str(exc)
    else:
        raise AssertionError("cross-plant maintenance memory must be rejected")


def test_memory_tag_mismatch_is_rejected():
    def provider(*, plant_id, tag):
        return [{"plant_id": plant_id, "tag": "FT-404"}]

    try:
        fetch_tenant_maintenance_memory("PLANT-A", "PT-303", provider)
    except ValueError as exc:
        assert "tag mismatch" in str(exc)
    else:
        raise AssertionError("maintenance memory tag mismatch must be rejected")


def test_no_provider_is_safe():
    result = fetch_tenant_maintenance_memory("PLANT-A", "PT-303")
    assert result["status"] == "NOT_INVOKED"
    assert result["records"] == []
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False
    assert result["safety"]["human_decision_required"] is True
