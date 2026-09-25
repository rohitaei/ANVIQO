import unittest

from anvi_intelligence_orchestrator import SAFETY, build_brief, classify, investigate


class TestANVIIntelligenceOrchestrator(unittest.TestCase):
    def test_classifies_hod_investigation(self):
        intents = classify("HOD: how is my plant, what changed and why?")
        self.assertIn("plant_brief", intents)
        self.assertIn("what_changed", intents)
        self.assertIn("root_cause", intents)
        self.assertIn("management", intents)

    def test_brief_is_evidence_based(self):
        rows = [
            {"tag": "PT303", "area": "VRM", "source": "PCI.xlsx", "record_type": "instrument"},
            {"tag": "FT101", "area": "RMHS", "source": "IO.xlsx", "record_type": "instrument"},
        ]
        brief = build_brief("plant-b", "MBF-2", rows)
        self.assertEqual(brief["status"], "EVIDENCE_AVAILABLE")
        self.assertEqual(brief["coverage"]["records"], 2)
        self.assertEqual(brief["coverage"]["tags"], 2)
        self.assertTrue(brief["read_only"])
        self.assertFalse(brief["plc_write"])
        self.assertTrue(brief["human_decision_required"])

    def test_investigation_preserves_existing_answer(self):
        result = investigate(
            "Why is PT303 important?",
            "plant-b",
            "MBF-2",
            lambda q: {"answer": "Verified PT303 evidence", "evidence_status": "EVIDENCE_AVAILABLE", "evidence": [{"tag": "PT303", "plant_id": "plant-b"}]},
        )
        self.assertEqual(result["answer"], "Verified PT303 evidence")
        self.assertEqual(result["context"]["plant_id"], "plant-b")
        self.assertEqual(result["evidence_status"], "EVIDENCE_AVAILABLE")
        self.assertTrue(result["decision"]["required"])
        self.assertFalse(result["decision"]["automatic_action"])


    def test_intelligence_fabric_uses_selected_plant_for_engineering_evidence(self):
        import anviqo_intelligence_fabric as fabric
        original_context = fabric.tenant_context
        original_rows = fabric._tenant_knowledge_rows
        original_loader = fabric.load
        try:
            fabric.tenant_context = lambda: ("plant-universal-a", "org-universal")
            fabric._tenant_knowledge_rows = lambda query, tag=None: [{
                "plant_id": "plant-universal-a",
                "organization_id": "org-universal",
                "tag": tag or "PT-101",
                "name": "Pressure transmitter",
            }]
            def forbidden_global_loader(name):
                if name == "pci_conversation":
                    raise AssertionError("global PCI conversation path used for tenant request")
                return original_loader(name)
            fabric.load = forbidden_global_loader
            result = fabric.pci("PT-101", "Tell me about PT-101")
            self.assertEqual(result["scope"], "SELECTED_PLANT_ONLY")
            self.assertEqual(result["plant_id"], "plant-universal-a")
            self.assertEqual(result["organization_id"], "org-universal")
            self.assertEqual(result["identity"]["plant_id"], "plant-universal-a")
        finally:
            fabric.tenant_context = original_context
            fabric._tenant_knowledge_rows = original_rows
            fabric.load = original_loader

    def test_intelligence_fabric_spares_do_not_use_global_pci_inventory_for_tenant(self):
        import anviqo_intelligence_fabric as fabric
        original_context = fabric.tenant_context
        original_rows = fabric._tenant_knowledge_rows
        original_loader = fabric.load
        try:
            fabric.tenant_context = lambda: ("plant-universal-b", "org-universal")
            fabric._tenant_knowledge_rows = lambda query, tag=None: [{
                "plant_id": "plant-universal-b",
                "organization_id": "org-universal",
                "tag": tag or "PT-202",
                "name": "Pressure transmitter spare",
                "content": "spare stock 2",
            }]
            def forbidden_global_loader(name):
                if name == "pci_spares":
                    raise AssertionError("global PCI spare inventory used for tenant request")
                return original_loader(name)
            fabric.load = forbidden_global_loader
            result = fabric.spares("PT-202", "spare for PT-202")
            self.assertEqual(result["scope"], "SELECTED_PLANT_ONLY")
            self.assertEqual(result["plant_id"], "plant-universal-b")
            self.assertEqual(result["records"][0]["tag"], "PT-202")
        finally:
            fabric.tenant_context = original_context
            fabric._tenant_knowledge_rows = original_rows
            fabric.load = original_loader

    def test_safety_contract_is_frozen(self):
        self.assertTrue(SAFETY["read_only"])
        self.assertFalse(SAFETY["plc_write"])
        self.assertFalse(SAFETY["scada_control"])
        self.assertFalse(SAFETY["automatic_authorization"])
        self.assertTrue(SAFETY["human_decision_required"])
        self.assertFalse(SAFETY["v5_intelligence_modified"])


    def test_realtime_evidence_state_keeps_safety_boundary(self):
        import anviqo_intelligence_fabric as fabric
        result = fabric.build_realtime_evidence_state("PT-303 current condition", "PT-303")
        self.assertEqual(result["version"], "ANVIQO-V2-REALTIME-EVIDENCE")
        self.assertFalse(result["safety"]["plc_write"])
        self.assertFalse(result["safety"]["scada_control"])
        self.assertFalse(result["safety"]["automatic_execution"])
        self.assertTrue(result["safety"]["human_decision_required"])


if __name__ == "__main__":
    unittest.main()
