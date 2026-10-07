from datetime import datetime, timezone
from anvi_global_v2_contracts import Evidence
from anvi_v2_evidence_ledger import appendable

def _evidence(plant):
    return Evidence(
        organization_id="org-a",
        plant_id=plant,
        evidence_type="TELEMETRY",
        source="S7",
        observed_at=datetime.now(timezone.utc).isoformat(),
        content={"tag":"PT-303","value":68.0},
        confidence="HIGH",
    )

def test_owned_evidence_is_accepted():
    result = appendable(_evidence("plant-a"), "org-a", "plant-a")
    assert result["accepted"] is True
    assert result["evidence_id"].startswith("EV-")

def test_foreign_evidence_is_rejected():
    result = appendable(_evidence("plant-b"), "org-a", "plant-a")
    assert result["accepted"] is False
    assert result["reason"] == "FOREIGN_PLANT_EVIDENCE_BLOCKED"
