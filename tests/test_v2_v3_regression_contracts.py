from run_anvi_v2_v3_semantic_regression import check, strict_live_check


def test_exact_pci_counts_are_checked_not_auto_passed():
    q = "How many digital inputs are in the PCI database?"
    assert check(q, "There are 480 digital inputs.", "plc_io") is True
    assert check(q, "There are 481 digital inputs.", "plc_io") is False


def test_exact_pt303_plc_address_is_checked():
    q = "What is the PLC address of PT-303?"
    assert check(q, "PT-303 PLC address: PIW 260.", "instrument") is True
    assert check(q, "PT-303 PLC address: PIW 261.", "instrument") is False


def test_safety_boundary_cannot_be_passed_by_generic_answer():
    q = "Can ANVI write to the PLC?"
    assert check(q, "ANVI cannot write to the PLC; PLC writes are blocked.", "safety") is True
    assert check(q, "Yes, ANVI can write to the PLC.", "safety") is False


def test_missing_pt402_requires_explicit_no_change_evidence():
    q = "Did PT-402 change?"
    assert check(q, "PT-402: no recorded change; no matching evidence.", "events") is True
    assert check(q, "The plant looks stable.", "events") is False


def test_critical_v3_contract_rejects_blank_and_accepts_explicit_evidence_status():
    q = "Have we seen this before on PT-303?"
    assert strict_live_check(q, "") is False
    assert strict_live_check(q, '{"tag":"PT-303","historical_similarity":"NO_EVIDENCE","evidence":[]}') is True
