import root_cause_intelligence as rci


def test_conversational_rci_intent():
    assert rci.is_root_cause_query("Why is PT-303 abnormal?") is True
    assert rci.is_root_cause_query("What is the cause of PT-303 failure?") is True
    assert rci.is_root_cause_query("Show me PT-303 details") is False
    assert rci.is_root_cause_query("How many PT-303 spares do we have?") is False
