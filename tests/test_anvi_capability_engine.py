import unittest

from anvi_capability_engine import catalog, coverage, manifest, resolve, execute


class TestUniversalCapabilityEngine(unittest.TestCase):
    def test_exactly_5000_capability_contracts(self):
        rows = catalog()
        self.assertEqual(len(rows), 5000)
        self.assertEqual(len({r["id"] for r in rows}), 5000)

    def test_manifest_formula(self):
        m = manifest()
        self.assertEqual(m["catalog_size"], 5000)
        self.assertEqual(m["architecture"]["formula"], "25 x 10 x 20 = 5,000")

    def test_capability_resolution(self):
        row = resolve("ANVI-REAL_TIME_OBSERVATION-IO_POINT-OBSERVE")
        self.assertIsNotNone(row)
        self.assertEqual(row["family"], "real_time_observation")

    def test_no_selected_plant_fails_closed(self):
        result = execute("ANVI-PLANT_HEALTH-PLANT-HEALTH", "plant health")
        self.assertEqual(result["status"], "BLOCKED_NO_SELECTED_PLANT")
        self.assertFalse(result["safety"]["plc_write"])
        self.assertFalse(result["safety"]["scada_control"])

    def test_coverage_is_explicit(self):
        c = coverage()
        self.assertEqual(c["catalog_size"], 5000)
        self.assertIn("coverage_percent", c)
        self.assertIn("unbacked_capabilities", c)


if __name__ == "__main__":
    unittest.main()
