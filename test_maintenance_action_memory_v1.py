from maintenance_action_memory_v1 import retrieve_actions, summarize_actions, SAFETY


def test_verified_action_retrieval():
    records = [{
        "memory_id": "PM-A3DF27161F0D",
        "tag": "PT-303",
        "finding": "Faulty transmitter",
        "maintenance_action": "Inspected and replaced transmitter",
        "confirmation_evidence": "Healthy signal restored",
        "verified": True,
    }]
    result = summarize_actions(records, tag="PT-303", symptom="faulty transmitter")
    assert result["count"] == 1
    assert result["matches"][0]["maintenance_action"].startswith("Inspected")
    assert result["matches"][0]["confirmation_evidence"] == "Healthy signal restored"
    assert result["matches"][0]["verified"] is True


def test_unverified_or_incomplete_memory_is_excluded():
    records = [
        {"tag": "PT-303", "maintenance_action": "Replace transmitter", "confirmation_evidence": "Signal healthy", "verified": False},
        {"tag": "PT-303", "maintenance_action": "Replace transmitter"},
        {"tag": "PT-303", "confirmation_evidence": "Signal healthy", "verified": True},
    ]
    assert retrieve_actions(records, tag="PT-303") == []


def test_mismatched_tag_is_excluded():
    records = [{
        "tag": "PT-304",
        "maintenance_action": "Inspected and replaced transmitter",
        "confirmation_evidence": "Healthy signal restored",
        "verified": True,
    }]
    assert retrieve_actions(records, tag="PT-303") == []


def test_safety_boundary():
    assert SAFETY["read_only"] is True
    assert SAFETY["plc_write"] is False
    assert SAFETY["scada_control"] is False
    assert SAFETY["automatic_execution"] is False
    assert SAFETY["human_decision_required"] is True
