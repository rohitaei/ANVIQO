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


if __name__ == "__main__":
    unittest.main()
