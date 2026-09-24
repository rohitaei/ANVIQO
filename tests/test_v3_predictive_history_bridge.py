from v3.predictive_history_bridge import fetch_tenant_predictive_history


def test_legacy_history_provider_is_blocked():
    def legacy(tag):
        return [{"tag": tag, "timestamp": "2026-09-22T10:00:00Z", "value": 10}]

    result = fetch_tenant_predictive_history("PLANT-A", "PT-303", legacy)
    assert result["status"] == "NOT_INVOKED"
    assert "legacy/global" in result["reason"]


def test_tenant_scoped_history_provider_is_invoked():
    def provider(*, plant_id, tag):
        return [
            {
                "plant_id": plant_id,
                "tag": tag,
                "timestamp": "2026-09-22T10:00:00Z",
                "value": 10,
            }
        ]

    result = fetch_tenant_predictive_history("PLANT-A", "PT-303", provider)
    assert result["status"] == "INVOKED"
    assert result["observation_count"] == 1
    assert result["observations"][0]["plant_id"] == "PLANT-A"


def test_cross_plant_history_row_is_rejected():
    def provider(*, plant_id, tag):
        return [{"plant_id": "PLANT-B", "tag": tag, "value": 10}]

    try:
        fetch_tenant_predictive_history("PLANT-A", "PT-303", provider)
    except ValueError as exc:
        assert "plant scope" in str(exc)
    else:
        raise AssertionError("cross-plant history must be rejected")


def test_history_tag_mismatch_is_rejected():
    def provider(*, plant_id, tag):
        return [{"plant_id": plant_id, "tag": "PT-304", "value": 10}]

    try:
        fetch_tenant_predictive_history("PLANT-A", "PT-303", provider)
    except ValueError as exc:
        assert "tag mismatch" in str(exc)
    else:
        raise AssertionError("history tag mismatch must be rejected")


def test_no_provider_is_safe():
    result = fetch_tenant_predictive_history("PLANT-A", "PT-303")
    assert result["status"] == "NOT_INVOKED"
    assert result["safety"] == {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "automatic_action": False,
        "human_decision_required": True,
    }
