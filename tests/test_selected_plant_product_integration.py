import ast
from pathlib import Path


def test_chat_uses_selected_plant_snapshot():
    text=Path("anvi_chat_stability_v2.py").read_text(encoding="utf-8")
    assert "def _selected_live_snapshot" in text
    # Direct unscoped simulator calls must not remain in the active chat engine.
    assert "snap = get_live_pci_snapshot()" not in text


def test_api_has_no_synthetic_maintenance_management_snapshot():
    text=Path("anviqo_api.py").read_text(encoding="utf-8")
    assert '"equipment": "CV-101"' not in text
    assert '"priority": 84.7' not in text


def test_api_syntax():
    for name in ("anvi_chat_stability_v2.py", "anviqo_api.py"):
        ast.parse(Path(name).read_text(encoding="utf-8"), filename=name)


def test_industrial_intelligence_route_is_tenant_backed():
    text=Path("anviqo_api.py").read_text(encoding="utf-8")
    assert 'SELECTED_PLANT_TENANT_KNOWLEDGE' in text
    assert 'NO_SELECTED_PLANT' in text
    assert 'run_industrial_intelligence(payload)' in text
