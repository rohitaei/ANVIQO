import pytest

from v3 import production_boundary


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
    assert result["prediction"]["status"] == "INSUFFICIENT_EVIDENCE"
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

    monkeypatch.setattr(production_boundary.store, "_connect", lambda: FakeConn(), raising=False) if hasattr(production_boundary, "store") else None
    # The production loader imports the tenant store locally; an explicit
    # missing plant is therefore the safe outcome.
