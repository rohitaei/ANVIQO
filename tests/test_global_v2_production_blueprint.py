from pathlib import Path

def test_global_blueprint_and_execution_plan_exist():
    assert Path("docs/ANVIQO_GLOBAL_V2_PRODUCTION_BLUEPRINT.md").exists()
    assert Path("docs/ANVIQO_GLOBAL_V2_FINAL_EXECUTION_PLAN.md").exists()

def test_global_blueprint_safety_is_explicit():
    text = Path("docs/ANVIQO_GLOBAL_V2_PRODUCTION_BLUEPRINT.md").read_text()
    assert "read_only=True" in text
    assert "plc_write=False" in text
    assert "scada_control=False" in text
    assert "automatic_execution=False" in text
    assert "human_decision_required=True" in text

def test_no_claim_of_live_certification():
    text = Path("docs/ANVIQO_GLOBAL_V2_FINAL_EXECUTION_PLAN.md").read_text()
    assert "No fake live data" in text
    assert "No production deployment without external certification" in text
