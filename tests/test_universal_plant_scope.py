import unittest

from anviqo_intelligence_fabric import extract_tag
from anvi_intelligence_orchestrator import _tenant_only


class UniversalPlantScopeTests(unittest.TestCase):
    def test_engineering_tag_extraction_is_not_pci_family_locked(self):
        self.assertEqual(extract_tag("Tell me about TIC_101A"), "TIC-101A")
        self.assertEqual(extract_tag("Check P-101A"), "P-101A")
        self.assertEqual(extract_tag("Show AREA-01-TAG-2"), "AREA-01-TAG-2")
        self.assertEqual(extract_tag("Tell me about PT-303"), "PT-303")

    def test_unscoped_legacy_dict_is_rejected(self):
        self.assertIsNone(_tenant_only({"tag": "TIC-101A"}, "plant-a"))

    def test_cross_plant_dict_is_rejected(self):
        self.assertIsNone(
            _tenant_only({"plant_id": "plant-b", "tag": "TIC-101A"}, "plant-a")
        )

    def test_same_plant_dict_is_accepted(self):
        value = {"plant_id": "plant-a", "tag": "TIC-101A"}
        self.assertEqual(_tenant_only(value, "plant-a"), value)

    def test_list_keeps_only_explicitly_owned_records(self):
        value = [
            {"plant_id": "plant-a", "tag": "TIC-101A"},
            {"plant_id": "plant-b", "tag": "PT-303"},
            {"tag": "FT-201"},
        ]
        self.assertEqual(
            _tenant_only(value, "plant-a"),
            [{"plant_id": "plant-a", "tag": "TIC-101A"}],
        )

    def test_authenticated_fabric_does_not_use_global_equipment_store(self):
        import anviqo_intelligence_fabric as fabric

        fabric.tenant_context = lambda: ("plant-b", "org-b")
        fabric.load = lambda name: (_ for _ in ()).throw(
            AssertionError("global module path used: " + name)
        )

        result = fabric.equipment("TIC-101A")
        self.assertEqual(result["scope"], "SELECTED_PLANT_ONLY")
        self.assertEqual(result["plant_id"], "plant-b")

    def test_authenticated_fabric_does_not_use_global_memory_store(self):
        import anviqo_intelligence_fabric as fabric

        fabric.tenant_context = lambda: ("plant-b", "org-b")
        fabric.load = lambda name: (_ for _ in ()).throw(
            AssertionError("global module path used: " + name)
        )

        self.assertEqual(fabric.verified_memory("TIC-101A"), [])


    def test_authenticated_fabric_does_not_use_global_plant_event_or_maintenance(self):
        import anviqo_intelligence_fabric as fabric

        fabric.tenant_context = lambda: ("plant-b", "org-b")
        fabric.load = lambda name: (_ for _ in ()).throw(
            AssertionError("global module path used: " + name)
        )

        self.assertEqual(fabric.plant()["scope"], "SELECTED_PLANT_ONLY")
        self.assertEqual(fabric.events("TIC-101A")["events"], [])
        self.assertEqual(fabric.maintenance("TIC-101A", "maintenance history")["matching_experience"], [])


if __name__ == "__main__":
    unittest.main()


def test_authenticated_unified_plant_evidence_never_uses_global_simulator(monkeypatch):
    from flask import Flask, session
    import anvi_knowledge_layer as layer

    app = Flask(__name__)
    app.secret_key = "test"

    def fail_global(*args, **kwargs):
        raise AssertionError("global plant evidence path used")

    monkeypatch.setattr(layer, "_build_area_results", fail_global)

    with app.test_request_context("/"):
        session["authenticated"] = True
        session["plant_id"] = "plant-b"
        session["organization_id"] = "org-b"
        monkeypatch.setattr(
            "anvi_tenant_chat_boundary._rows",
            lambda plant_id, terms=None, tag=None, limit=2500: [
                {"plant_id": plant_id, "area": "AREA-X", "tag": "TIC-101A"}
            ],
        )

        result = layer._build_unified_plant_evidence_context()

    assert result["plant"] == "plant-b"
    assert result["source"] == ["SELECTED_PLANT_KNOWLEDGE"]
    assert result["tenant_scope"]["plant_id"] == "plant-b"
    assert result["evidence_available"] is True
    assert result["areas"][0]["area"] == "AREA-X"
