import unittest

from v2.contracts import IndustrialPoint
from v2.data_fabric import ReadOnlyDataFabric
from v2.source_adapters import FabricSourceRunner, PciDemoStreamAdapter


class TestPciDemoAdapter(unittest.TestCase):
    def test_normalizes_existing_demo_points(self):
        raw = {"points": [{"tag": "PT-303", "value": 42.5, "state": "HEALTHY",
                           "timestamp": "2026-01-01T00:00:00+00:00",
                           "source": "PCI DEMO STREAM", "mode": "SIMULATION"}]}
        adapter = PciDemoStreamAdapter(lambda: raw)
        points = list(adapter.read("plant-a"))
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].plant_id, "plant-a")
        self.assertEqual(points[0].tag, "PT-303")
        self.assertEqual(points[0].source, "PCI DEMO STREAM")
        self.assertEqual(points[0].mode, "SIMULATION")

    def test_runner_feeds_fabric_without_cross_plant_data(self):
        raw = {"points": [{"tag": "PT-303", "value": 10,
                           "timestamp": "2026-01-01T00:00:00+00:00",
                           "source": "PCI DEMO STREAM", "mode": "SIMULATION"}]}
        fabric = ReadOnlyDataFabric()
        FabricSourceRunner(fabric, PciDemoStreamAdapter(lambda: raw)).poll_once("plant-a")
        self.assertIsNotNone(fabric.latest("plant-a", "PT-303"))
        self.assertIsNone(fabric.latest("plant-b", "PT-303"))

    def test_runner_preserves_safety_boundary(self):
        raw = {"points": [{"tag": "PT-303", "value": 10,
                           "timestamp": "2026-01-01T00:00:00+00:00",
                           "source": "PCI DEMO STREAM", "mode": "SIMULATION"}]}
        fabric = ReadOnlyDataFabric()
        FabricSourceRunner(fabric, PciDemoStreamAdapter(lambda: raw)).poll_once("plant-a")
        health = fabric.health("plant-a").to_dict()
        self.assertTrue(health["read_only"])
        self.assertFalse(health["plc_write"])
        self.assertFalse(health["scada_control"])
        self.assertTrue(health["human_decision_required"])


if __name__ == "__main__":
    unittest.main()
