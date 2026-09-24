from v2.event_context import LiveEventContext
from v2.v5_live_what_changed import run_live_v5_what_changed


def context(plant):
    return LiveEventContext(
        plant_id=plant,
        state="WATCH",
        changed_points=[{"tag": "PT-303", "current_value": 12}],
        equipment_context=[],
        v5_what_changed=None,
        safety={
            "read_only": True,
            "plc_write": False,
            "scada_control": False,
            "automatic_action": False,
            "human_decision_required": True,
        },
    )


def test_live_bridge_passes_tenant_scoped_area_evidence_to_existing_v5():
    calls = []

    def provider(plant_id):
        calls.append(plant_id)
        return [{
            "plant_id": plant_id,
            "area": "AREA-A",
            "status": "HEALTHY",
            "health_score": 90,
            "equipment": [],
        }]

    def existing_v5(plant, areas, equipment_events=None):
        return {"engine": "V5", "plant": plant, "area_count": len(areas)}

    result = run_live_v5_what_changed(
        context("PLANT-A"),
        provider,
        v5_builder=existing_v5,
    )

    assert calls == ["PLANT-A"]
    assert result["status"] == "V5_WHAT_CHANGED_COMPLETE"
    assert result["result"]["engine"] == "V5"
    assert result["result"]["plant"] == "PLANT-A"


def test_live_bridge_rejects_cross_plant_provider_output():
    def provider(_plant_id):
        return [{"plant_id": "PLANT-B", "area": "OTHER"}]

    try:
        run_live_v5_what_changed(context("PLANT-A"), provider)
    except ValueError as exc:
        assert "different plant" in str(exc)
    else:
        raise AssertionError("cross-plant evidence was accepted")


def test_live_bridge_does_not_global_fallback_when_provider_has_no_data():
    calls = []

    def provider(plant_id):
        calls.append(plant_id)
        return []

    def existing_v5(plant, areas, equipment_events=None):
        return {"plant": plant, "areas": areas}

    result = run_live_v5_what_changed(
        context("PLANT-B"),
        provider,
        v5_builder=existing_v5,
    )

    assert calls == ["PLANT-B"]
    assert result["result"]["plant"] == "PLANT-B"
    assert result["result"]["areas"] == []


def test_live_bridge_preserves_safety():
    def provider(plant_id):
        return [{"plant_id": plant_id, "area": "A"}]

    result = run_live_v5_what_changed(
        context("PLANT-A"),
        provider,
        v5_builder=lambda plant, areas, equipment_events=None: {"ok": True},
    )

    assert result["safety"]["read_only"] is True
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False
    assert result["safety"]["automatic_action"] is False
    assert result["safety"]["human_decision_required"] is True
