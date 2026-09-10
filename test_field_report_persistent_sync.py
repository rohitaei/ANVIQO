import field_report_persistent_sync as sync


def test_durable_record_round_trip(monkeypatch):
    calls = []
    rows = []

    def fake_exec(sql, params=None, fetch=False):
        calls.append((sql, params, fetch))
        if "SELECT before_qty" in sql:
            return rows
        return None

    monkeypatch.setattr(sync, "_neon_ready", lambda: True)
    import anvi_neon_store
    monkeypatch.setattr(anvi_neon_store, "_exec", fake_exec)

    assert sync.record_applied("PM-1", "pt_303", 1, 3, 2, "TX-1") is True
    assert calls
    assert calls[-1][1] == ("PM-1", "PT_303", 1.0, 3.0, 2.0, "TX-1")

    rows[:] = [(3, 2, "TX-1")]
    result = sync.get_applied("PM-1", "PT_303", 1)
    assert result["status"] == "ALREADY_APPLIED"
    assert result["inventory_changed"] is False
    assert result["before"] == 3
    assert result["after"] == 2
    assert result["transaction_id"] == "TX-1"


def test_durable_guard_is_scoped_to_report_tag_and_quantity(monkeypatch):
    import anvi_neon_store

    def fake_exec(sql, params=None, fetch=False):
        if "SELECT before_qty" in sql:
            if params == ("PM-2", "PT-303", 1.0):
                return [(5, 4, "TX-2")]
            return []
        return None

    monkeypatch.setattr(sync, "_neon_ready", lambda: True)
    monkeypatch.setattr(anvi_neon_store, "_exec", fake_exec)

    assert sync.get_applied("PM-2", "PT-303", 1)["transaction_id"] == "TX-2"
    assert sync.get_applied("PM-2", "PT-303", 2) is None
    assert sync.get_applied("PM-OTHER", "PT-303", 1) is None
