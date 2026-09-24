from datetime import datetime, timezone

from v2.contracts import IndustrialPoint
from v2.data_fabric import ReadOnlyDataFabric
from v2.data_trust import DataTrustPolicy
from v2.plant_brain import LivePlantBrain


def test_plant_brain_is_tenant_scoped_and_reuses_bridge():
    fabric = ReadOnlyDataFabric()
    fabric.ingest(IndustrialPoint(
        plant_id="plant-a",
        tag="TEMP-1",
        timestamp="2026-09-21T09:59:55+00:00",
        value=80,
        source="UNIVERSAL TEST",
        quality="GOOD",
    ))
    fabric.ingest(IndustrialPoint(
        plant_id="plant-b",
        tag="TEMP-1",
        timestamp="2026-09-21T09:59:55+00:00",
        value=20,
        source="UNIVERSAL TEST",
        quality="GOOD",
    ))

    calls = []

    def v5_bridge(**kwargs):
        calls.append(kwargs["plant_id"])
        return {"engine": "EXISTING V5"}

    brain = LivePlantBrain(
        fabric,
        DataTrustPolicy(),
        v5_bridge=v5_bridge,
    )
    result = brain.run_once("plant-a")

    assert result["plant_id"] == "plant-a"
    assert result["points_seen"] == 1
    assert result["evidence"]["TEMP-1"]["point"]["value"] == 80
    assert "plant-b" not in str(result)
    assert result["v5"]["status"] == "INVOKED"
    assert calls == ["plant-a"]


def test_untrusted_evidence_is_explicit():
    fabric = ReadOnlyDataFabric()
    fabric.ingest(IndustrialPoint(
        plant_id="plant-a",
        tag="PT-1",
        timestamp="not-a-time",
        value=10,
        source="UNIVERSAL TEST",
        quality="GOOD",
    ))
    result = LivePlantBrain(fabric).observe("plant-a").to_dict()
    assert result["untrusted_points"] == 1
    assert result["fresh_points"] == 0
    assert result["evidence"]["PT-1"]["trust"]["accepted"] is False


def test_safety_boundary():
    fabric = ReadOnlyDataFabric()
    result = LivePlantBrain(fabric).observe("plant-a").to_dict()
    assert result["safety"] == {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "automatic_action": False,
        "human_decision_required": True,
    }
