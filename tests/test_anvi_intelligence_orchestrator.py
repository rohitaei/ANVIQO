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
