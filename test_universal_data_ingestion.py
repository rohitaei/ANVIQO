from pathlib import Path
import json

from universal_data_ingestion import connector_contract, ingest_file, ingest_records


def test_json_ingestion_normalizes_without_reasoning_changes(tmp_path):
    source = tmp_path / "plant.json"
    source.write_text(json.dumps({
        "plant": {"organization_id": "org-demo", "plant_id": "plant-demo", "plant_name": "Demo Plant", "industry": "Steel"},
        "records": [
            {"id": "LT-303", "description": "Level transmitter", "unit": "PCI", "instrument_type": "LT"}
        ],
    }), encoding="utf-8")
    result = ingest_file(source)
    assert result["contract"] == "ANVIQO-ONBOARDING-V1"
    assert result["plant"]["plant_id"] == "plant-demo"
    assert result["records"][0]["external_id"] == "LT-303"
    assert result["records"][0]["area"] == "PCI"
    assert result["ingestion"]["approved_connector"] is True
    assert result["safety"]["plc_write"] is False
    assert result["safety"]["scada_control"] is False


def test_csv_ingestion_uses_configured_plant_identity(tmp_path):
    source = tmp_path / "assets.csv"
    source.write_text("asset_id,equipment_name,location,service\nP-101,Feed Pump,RMHS,Raw Material\n", encoding="utf-8")
    result = ingest_file(source, {"organization_id": "org-a", "plant_id": "plant-a", "name": "Plant A"})
    assert result["records"][0]["external_id"] == "P-101"
    assert result["records"][0]["name"] == "Feed Pump"
    assert result["records"][0]["area"] == "RMHS"


def test_connector_neutral_records_and_safety():
    result = ingest_records(
        {"organization_id": "org-b", "plant_id": "plant-b", "name": "Plant B", "industry": "Cement"},
        [{"tag_name": "PT-303", "equipment_name": "Gas pressure transmitter", "location": "Mill"}],
        source="approved_vendor_adapter",
    )
    assert result["records"][0]["external_id"] == "PT-303"
    assert result["ingestion"]["approved_connector"] is True
    assert result["safety"]["plc_write"] is False
    assert result["reasoning_engine"] == "existing_v5_intelligence_only"


def test_contract_is_explicitly_read_only():
    contract = connector_contract()
    assert contract["approved_connector"] is True
    assert contract["control_operations"] is False
    assert contract["safety"]["plc_write"] is False
    assert contract["safety"]["scada_control"] is False
    assert contract["principle"] == "CHANGE DATA, NOT CODE"
