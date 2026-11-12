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


def test_tenant_observation_history_is_isolated_by_org_and_plant(tmp_path, monkeypatch):
    import anvi_tenant_store as store
    import failure_prediction_history as history

    monkeypatch.setattr(store, "TENANT_DB_URL", "sqlite:///" + str(tmp_path / "tenant.db"))
    monkeypatch.setattr(store, "DATABASE_URL", "")
    store.init_schema()

    common = dict(
        plant_id="plant-shared-test", tag="PT-303", value=42.0,
        timestamp="2026-11-12T10:00:00+00:00", source_type="LIVE_TELEMETRY",
        source="read-only gateway", unit="bar", state="HEALTHY",
        area="PCI", provenance="signed gateway sample",
    )
    history.record_tenant_observation(organization_id="org-a", user_id="user-a", **common)
    other = dict(common)
    other["value"] = 99.0
    history.record_tenant_observation(organization_id="org-b", user_id="user-b", **other)

    a = history.get_tenant_observations("org-a", "plant-shared-test", "PT-303")
    b = history.get_tenant_observations("org-b", "plant-shared-test", "PT-303")
    assert len(a) == 1 and a[0]["value"] == 42.0
    assert len(b) == 1 and b[0]["value"] == 99.0
    assert history.get_tenant_observations("org-c", "plant-shared-test", "PT-303") == []
