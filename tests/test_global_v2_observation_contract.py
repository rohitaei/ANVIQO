from datetime import datetime, timezone
from anvi_global_v2_contracts import normalize_observation, assert_tenant, safety_contract

def test_normalized_observation():
    result = normalize_observation(
        organization_id="org-a",
        plant_id="plant-a",
        tag="PT-303",
        timestamp=datetime.now(timezone.utc).isoformat(),
        value=42.0,
        quality="GOOD",
        unit="bar",
        source_protocol="S7",
        source_address="DB1.DBW10",
    )
    assert result["valid"] is True
    assert result["observation"]["tag"] == "PT-303"

def test_foreign_plant_is_blocked():
    try:
        assert_tenant("org-a", "plant-b", "org-a", "plant-a")
    except PermissionError as exc:
        assert "FOREIGN_PLANT" in str(exc)
    else:
        raise AssertionError("Foreign plant evidence was not blocked")

def test_safety_contract():
    safety = safety_contract()
    assert safety == {
        "read_only": True,
        "plc_write": False,
        "scada_control": False,
        "automatic_authorization": False,
        "automatic_execution": False,
        "human_decision_required": True,
    }
