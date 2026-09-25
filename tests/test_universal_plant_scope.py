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


def test_authenticated_maintenance_never_reads_global_memory(monkeypatch):
    from flask import Flask, session
    import anvi_knowledge_layer as layer

    app = Flask(__name__)
    app.secret_key = "test"

    def fail_global(*args, **kwargs):
        raise AssertionError("global Plant Memory used")

    monkeypatch.setattr("plant_memory.search_memory", fail_global)

    with app.test_request_context("/"):
        session["authenticated"] = True
        session["plant_id"] = "plant-b"
        session["organization_id"] = "org-b"
        monkeypatch.setattr(
            "anvi_tenant_chat_boundary._rows",
            lambda plant_id, terms=None, tag=None, limit=250: [
                {"plant_id": plant_id, "tag": tag, "verified": True}
            ],
        )
        result = layer._maintenance("maintenance history for TIC-101A")

    assert "plant_memory_count" in result
    assert '"plant-b"' in result


def test_authenticated_root_cause_never_uses_global_sources(monkeypatch):
    from flask import Flask, session
    import root_cause_intelligence as rci

    app = Flask(__name__)
    app.secret_key = "test"
    monkeypatch.setattr(rci, "_tenant_evidence", lambda tag, plant_id: [{"plant_id": plant_id, "tag": tag, "value": 12.3, "verified": True}])
    monkeypatch.setattr(rci, "_events", lambda tag: (_ for _ in ()).throw(AssertionError("global events used")))
    monkeypatch.setattr(rci, "_verified_memory", lambda tag: (_ for _ in ()).throw(AssertionError("global memory used")))
    monkeypatch.setattr(rci, "_health", lambda tag: (_ for _ in ()).throw(AssertionError("global health used")))
    monkeypatch.setattr(rci, "_pci_evidence", lambda tag, query: (_ for _ in ()).throw(AssertionError("global PCI used")))

    with app.test_request_context("/"):
        session["authenticated"] = True
        session["plant_id"] = "plant-b"
        session["organization_id"] = "org-b"
        result = rci.build_root_cause_intelligence("Why is TIC-101A abnormal?")

    assert result["tenant_scope"]["plant_id"] == "plant-b"
    assert result["evidence_summary"]["selected_plant_evidence_count"] == 1


def test_authenticated_plant_brain_uses_selected_plant_only(monkeypatch):
    from flask import Flask, session
    import plant_brain_reasoning as brain

    app = Flask(__name__)
    app.secret_key = "test"
    monkeypatch.setattr(brain, "build_area_equipment_intelligence", lambda area: (_ for _ in ()).throw(AssertionError("global V5 area intelligence used")))
    monkeypatch.setattr(brain, "_authenticated_tenant", lambda: ("plant-b", "org-b"))
    monkeypatch.setattr("anvi_tenant_chat_boundary._rows", lambda plant_id, terms=None, tag=None, limit=500: [{"plant_id": plant_id, "area": "AREA-X", "tag": "TIC-101A"}])

    with app.test_request_context("/"):
        session["authenticated"] = True
        session["plant_id"] = "plant-b"
        session["organization_id"] = "org-b"
        result = brain.build_plant_brain("AREA-X")

    assert result["tenant_scope"]["plant_id"] == "plant-b"
    assert result["evidence_rows"][0]["tag"] == "TIC-101A"


def test_authenticated_product_facade_never_uses_global_equipment_event_or_executive(monkeypatch):
    from flask import Flask, session
    import anviqo_product as product_module

    app = Flask(__name__)
    app.secret_key = "test"
    monkeypatch.setattr(product_module, "_tenant_rows", lambda plant_id, tag=None, limit=2500: [{"plant_id": plant_id, "tag": tag or "TIC-101A", "event_type": "TEST"}])
    monkeypatch.setattr("equipment_database.get_equipment", lambda *a, **k: (_ for _ in ()).throw(AssertionError("global equipment used")))
    monkeypatch.setattr("event_timeline.build_event_timeline", lambda *a, **k: (_ for _ in ()).throw(AssertionError("global events used")))
    monkeypatch.setattr("v57_executive_intelligence.build_executive_intelligence", lambda *a, **k: (_ for _ in ()).throw(AssertionError("global executive used")))

    with app.test_request_context("/"):
        session["authenticated"] = True
        session["plant_id"] = "plant-b"
        session["organization_id"] = "org-b"
        p = product_module.AnviqoProduct()
        assert p.equipment_view("TIC-101A")["plant_id"] == "plant-b"
        assert p.event_timeline("TIC-101A")["scope"] == "SELECTED_PLANT_ONLY"
        assert p.executive_view()["evidence_count"] == 1



def test_authenticated_product_facade_never_uses_global_equipment_relationships_events_or_hod(monkeypatch):
    from flask import Flask, session
    from anviqo_product import AnviqoProduct

    app = Flask(__name__)
    app.secret_key = "test"
    product = AnviqoProduct()

    monkeypatch.setattr(
        "anvi_tenant_chat_boundary._rows",
        lambda plant_id, terms=None, tag=None, limit=2500: [
            {"plant_id": plant_id, "tag": tag or "TIC-101A", "area": "AREA-X"}
        ],
    )
    monkeypatch.setattr(
        "equipment_database.get_equipment",
        lambda tag: (_ for _ in ()).throw(AssertionError("global equipment used")),
    )
    monkeypatch.setattr(
        "equipment_relationships.build_equipment_relationships",
        lambda tag: (_ for _ in ()).throw(AssertionError("global relationships used")),
    )
    monkeypatch.setattr(
        "event_timeline.build_event_timeline",
        lambda tag: (_ for _ in ()).throw(AssertionError("global events used")),
    )
    monkeypatch.setattr(
        "v57_executive_intelligence.build_executive_intelligence",
        lambda: (_ for _ in ()).throw(AssertionError("global HOD intelligence used")),
    )

    with app.test_request_context("/"):
        session["authenticated"] = True
        session["plant_id"] = "plant-b"
        session["organization_id"] = "org-b"

        assert product.equipment_view("TIC-101A")["scope"] == "SELECTED_PLANT_ONLY"
        assert product.relationships("TIC-101A")["scope"] == "SELECTED_PLANT_ONLY"
        assert product.event_timeline("TIC-101A")["scope"] == "SELECTED_PLANT_ONLY"
        assert product.executive_view()["scope"] == "SELECTED_PLANT_ONLY"
