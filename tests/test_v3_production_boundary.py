import pytest

from v3 import production_boundary
import anvi_tenant_store as store


def _package():
    return {
        "plant": {"plant_id": "PLANT-A", "organization_id": "ORG-1"},
        "records": [
            {
                "record_type": "INSTRUMENT",
                "external_id": "PT-303",
                "tag": "PT-303",
                "metadata": {},
            }
        ],
    }


def test_alpha20_production_flow_uses_tenant_package(monkeypatch):
    calls = {}

    def fake_loader(plant_id, organization_id):
        calls["scope"] = (plant_id, organization_id)
        return _package()

    monkeypatch.setattr(
        production_boundary,
        "load_tenant_onboarding_package",
        fake_loader,
    )

    result = production_boundary.run_production_predictive_flow(
        plant_id="PLANT-A",
        organization_id="ORG-1",
        tag="PT-303",
        observations=[
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0},
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:01:00Z", "value": 10.2},
        ],
    )

    assert calls["scope"] == ("PLANT-A", "ORG-1")
    assert result["plant_id"] == "PLANT-A"
    assert result["tag"] == "PT-303"
    assert result["prediction"]["status"] == "INVOKED"
    assert result["execution_audit"]["plant_id"] == "PLANT-A"


def test_alpha20_package_loader_rejects_missing_tenant_scope(monkeypatch):
    with pytest.raises(ValueError):
        production_boundary.load_tenant_onboarding_package("", "ORG-1")
    with pytest.raises(ValueError):
        production_boundary.load_tenant_onboarding_package("PLANT-A", "")


def test_alpha20_package_loader_rejects_unauthorized_organization(monkeypatch):
    class FakeCursor:
        def execute(self, *args):
            return None

        def fetchone(self):
            return None

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(store, "init_schema", lambda: None)
    monkeypatch.setattr(store, "_placeholder", lambda: "?")
    monkeypatch.setattr(store, "_connect", lambda: FakeConn())
    with pytest.raises(PermissionError):
        production_boundary.load_tenant_onboarding_package("PLANT-A", "ORG-1")



def test_alpha24_production_loader_reads_only_scoped_normalized_knowledge(monkeypatch):
    calls = []
    class FakeCursor:
        def __init__(self):
            self.kind = None
        def execute(self, sql, params=()):
            calls.append((sql, params))
            self.kind = "plant" if "FROM anviqo_plants" in sql else "knowledge"
        def fetchone(self):
            if self.kind == "plant":
                return ("Demo Plant", "steel")
            return None
        def fetchall(self):
            if self.kind == "knowledge":
                return [(
                    "INSTRUMENT", "PT-303", "Mill outlet pressure", "VRM/MILL",
                    "Mill gas", "PRESSURE", "PT-303", None, "MBF-2",
                    '{"pci_identity":{"plant_id":"PLANT-A","tag":"PT-303"}}',
                    "normalized evidence",
                )]
            return []
    class FakeConn:
        def __init__(self):
            self._cursor = FakeCursor()
        def cursor(self):
            return self._cursor
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(store, "init_schema", lambda: None)
    monkeypatch.setattr(store, "_placeholder", lambda: "?")
    monkeypatch.setattr(store, "_connect", lambda: FakeConn())

    package = production_boundary.load_tenant_onboarding_package("PLANT-A", "ORG-1")

    assert package["plant"]["plant_id"] == "PLANT-A"
    assert package["plant"]["organization_id"] == "ORG-1"
    assert package["plant"]["industry"] == "steel"
    assert len(package["records"]) == 1
    assert package["records"][0]["tag"] == "PT-303"
    assert package["records"][0]["pci_identity"]["plant_id"] == "PLANT-A"
    assert all("ORG-1" in str(params) for _, params in calls)


def test_alpha24_production_flow_preserves_loaded_tenant_package(monkeypatch):
    package = _package()
    captured = {}

    monkeypatch.setattr(
        production_boundary,
        "load_tenant_onboarding_package",
        lambda plant_id, organization_id: package,
    )

    def fake_package_flow(plant_id, tag, observations, **kwargs):
        captured.update({
            "plant_id": plant_id,
            "tag": tag,
            "observations": observations,
            "package": kwargs["package"],
        })
        return {"plant_id": plant_id, "tag": tag, "status": "PACKAGE_REACHED"}

    monkeypatch.setattr(
        production_boundary,
        "run_predictive_flow_from_package",
        fake_package_flow,
    )

    result = production_boundary.run_production_predictive_flow(
        plant_id="PLANT-A",
        organization_id="ORG-1",
        tag="PT-303",
        observations=[],
    )

    assert result["status"] == "PACKAGE_REACHED"
    assert captured["plant_id"] == "PLANT-A"
    assert captured["tag"] == "PT-303"
    assert captured["package"] is package


def test_alpha26_production_flow_injects_tenant_history_provider(monkeypatch):
    captured = {}

    package = {
        "plant": {"plant_id": "PLANT-A", "organization_id": "ORG-1", "name": "Demo", "industry": "steel"},
        "records": [{"tag": "PT-303", "external_id": "PT-303", "metadata": {}}],
    }

    monkeypatch.setattr(
        production_boundary,
        "load_tenant_onboarding_package",
        lambda plant_id, organization_id: package,
    )

    import failure_prediction_history as history
    monkeypatch.setattr(
        history,
        "get_tenant_observations",
        lambda **kwargs: captured.setdefault("history_scope", kwargs) or [],
    )

    def fake_flow(*args, **kwargs):
        captured["flow"] = kwargs
        provider = kwargs["history_provider"]
        captured["history"] = provider(plant_id="PLANT-A", tag="PT-303")
        return {"status": "TEST"}

    monkeypatch.setattr(production_boundary, "run_predictive_flow_from_package", fake_flow)

    result = production_boundary.run_production_predictive_flow(
        plant_id="PLANT-A",
        organization_id="ORG-1",
        tag="PT-303",
        observations=[
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:00:00Z", "value": 10.0},
            {"plant_id": "PLANT-A", "tag": "PT-303", "timestamp": "2026-09-20T10:01:00Z", "value": 10.2},
        ],
    )

    assert result["status"] == "TEST"
    assert captured["flow"]["history_provider"] is not None
    assert captured["history_scope"] == {
        "plant_id": "PLANT-A",
        "organization_id": "ORG-1",
        "tag": "PT-303",
    }
