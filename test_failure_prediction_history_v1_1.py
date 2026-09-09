import importlib


def test_observation_history_requires_provenance_and_rejects_simulation(tmp_path, monkeypatch):
    import failure_prediction_history as history
    monkeypatch.setattr(history, "HISTORY_DIR", tmp_path)
    monkeypatch.setattr(history, "HISTORY_FILE", tmp_path / "observation_history.json")
    history.record_observation(
        "PT303", 41.0, "2026-09-01T10:00:00+00:00",
        "LIVE_TELEMETRY", "read-only telemetry", "kg/cm2", "HEALTHY", "PCI", "source=plant telemetry"
    )
    history.record_observation(
        "PT-303", 49.0, "2026-09-08T10:00:00+00:00",
        "LIVE_TELEMETRY", "read-only telemetry", "kg/cm2", "WARNING", "PCI", "source=plant telemetry"
    )
    rows = history.get_observations("PT 303")
    assert len(rows) == 2
    assert rows[0]["tag"] == "PT-303"
    assert rows[1]["value"] == 49.0

    try:
        history.record_observation("PT-303", 50, source_type="LIVE_TELEMETRY", source="DEMO SIMULATION", provenance="demo")
        assert False, "simulation observation must be rejected"
    except ValueError as exc:
        assert "simulation" in str(exc).lower()


def test_observation_history_is_idempotent(tmp_path, monkeypatch):
    import failure_prediction_history as history
    monkeypatch.setattr(history, "HISTORY_DIR", tmp_path)
    monkeypatch.setattr(history, "HISTORY_FILE", tmp_path / "observation_history.json")
    kwargs = dict(tag="PT-303", value=42, timestamp="2026-09-01T10:00:00+00:00", source_type="LIVE_TELEMETRY", source="read-only telemetry", provenance="source=plant telemetry")
    first = history.record_observation(**kwargs)
    second = history.record_observation(**kwargs)
    assert first["observation_id"] == second["observation_id"]
    assert len(history.get_observations("PT-303")) == 1
