"""Global V2 contract tests. These tests do not enable PLC/SCADA writes."""
from pathlib import Path

SAFETY = {
    "read_only": True,
    "plc_write": False,
    "scada_control": False,
    "automatic_authorization": False,
    "automatic_execution": False,
    "human_decision_required": True,
}

def test_v2_documents_exist():
    root = Path(__file__).parents[1]
    for name in (
        "docs/ANVIQO_GLOBAL_V2_ARCHITECTURE.md",
        "docs/ANVIQO_GLOBAL_V2_CAPABILITY_MATRIX.md",
        "docs/ANVIQO_GLOBAL_V2_SAFETY_AND_SECURITY.md",
        "docs/ANVIQO_GLOBAL_V2_EDGE_CONTRACT.md",
        "docs/ANVIQO_GLOBAL_V2_TEST_PLAN.md",
        "docs/ANVIQO_GLOBAL_V2_BACKLOG.md",
    ):
        assert (root / name).exists()

def test_safety_contract_is_read_only():
    assert SAFETY["read_only"] is True
    assert SAFETY["plc_write"] is False
    assert SAFETY["scada_control"] is False
    assert SAFETY["automatic_authorization"] is False
    assert SAFETY["automatic_execution"] is False
    assert SAFETY["human_decision_required"] is True
