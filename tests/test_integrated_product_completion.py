"""Integrated ANVIQO product completion gate.

This gate checks the connected product contract:
admin plant creation -> universal onboarding -> normalized plant knowledge ->
tenant-scoped intelligence -> human-governed safety.
It intentionally does not modify frozen V5 intelligence engines.
"""
from pathlib import Path
import ast
import json

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="ignore")


def test_universal_onboarding_is_connected():
    onboarding = read("anvi_universal_onboarding.py")
    importer = read("anvi_plant_data_import.py")
    admin = read("anvi_plant_auth_routes.py")
    ui = read("anvi_plant_data_upload.html")

    assert "/admin/onboarding" in onboarding
    assert "/api/admin/onboarding/plant/<plant_id>/documents" in onboarding
    assert "/api/admin/onboarding/plant/<plant_id>/import" in importer
    assert "/api/admin/onboarding/plant/<plant_id>/import-status" in importer
    assert "/api/admin/onboarding/plant/<plant_id>/knowledge-summary" in importer
    assert "create_plant" in admin
    assert "import_plant_data" in importer
    assert "Make Data Available to ANVI" in ui
    assert "knowledge-summary" in ui


def test_tenant_scope_exists_at_product_boundaries():
    onboarding = read("anvi_universal_onboarding.py")
    importer = read("anvi_plant_data_import.py")
    command_centre = read("anvi_universal_command_centre.py")
    knowledge = read("anvi_knowledge_layer.py")

    assert "organization_id" in onboarding
    assert "organization_id" in importer
    assert "plant_id" in importer
    assert "_tenant_snapshot" in command_centre
    assert "_authenticated_tenant_context" in knowledge


def test_human_governed_safety_contract_is_present():
    files = (
        "anviqo_api.py",
        "anvi_knowledge_layer.py",
        "anvi_field_report.py",
        "pci_spares.py",
        "pci_conversation.py",
        "pci_live_simulator.py",
        "anvi_voice.py",
        "anvi_universal_onboarding.py",
        "anvi_plant_data_import.py",
    )
    for name in files:
        source = read(name).lower()
        assert "plc_write" in source, name
        assert "scada_control" in source, name
        assert "human_decision_required" in source, name
        assert "plc_write = true" not in source, name
        assert "scada_control = true" not in source, name


def test_pci_reference_data_contract():
    data = json.loads(read("database/pci/pci_instrument_database.json"))
    assert data["version"] == "PCI-1.0"
    assert data["control_mode"] == "READ_ONLY"
    assert data["plc_write"] is False
    assert data["scada_control"] is False
    assert data["human_decision_required"] is True
    assert data["record_count"] == 1064
    assert any(str(r.get("tag", "")).strip() == "PT_303" for r in data["records"])


def test_active_python_modules_parse():
    for name in (
        "anviqo_api.py",
        "anviqo_spare_query_guard.py",
        "anvi_plant_auth_routes.py",
        "anvi_plant_runtime_bridge.py",
        "anvi_universal_onboarding.py",
        "anvi_plant_data_import.py",
        "anvi_knowledge_layer.py",
    ):
        ast.parse(read(name), filename=name)


def test_command_centre_has_system_management_hook():
    bridge = read("anvi_plant_runtime_bridge.py")
    assert "Plant &amp; User Management" in bridge
