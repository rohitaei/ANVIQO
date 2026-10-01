import json
import os

import pytest

from anvi_edge_ingest import authenticate_gateway


def test_gateway_registry_is_plant_bound(monkeypatch):
    monkeypatch.setenv("ANVI_EDGE_GATEWAYS_JSON", json.dumps({
        "GW1": {"token": "secret", "plant_id": "P1", "organization_id": "O1"}
    }))
    assert authenticate_gateway("GW1", "secret")["plant_id"] == "P1"
    assert authenticate_gateway("GW1", "wrong") is None
    assert authenticate_gateway("GW2", "secret") is None


def test_registry_rejects_missing_scope(monkeypatch):
    monkeypatch.setenv("ANVI_EDGE_GATEWAYS_JSON", json.dumps({
        "GW1": {"token": "secret", "plant_id": "", "organization_id": "O1"}
    }))
    assert authenticate_gateway("GW1", "secret") is None
