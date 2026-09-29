import unittest

from plc_readonly_adapter import (
    AdapterValidationError,
    SAFETY,
    build_simulation_snapshot,
    normalize_observation,
    validate_live_enablement,
)


class TestPLCReadOnlyAdapter(unittest.TestCase):
    def test_safety_contract_is_write_blocked(self):
        self.assertTrue(SAFETY["read_only"])
        self.assertFalse(SAFETY["plc_write"])
        self.assertFalse(SAFETY["scada_control"])
        self.assertTrue(SAFETY["human_decision_required"])

    def test_simulation_snapshot_is_deterministic_and_normalized(self):
        result = build_simulation_snapshot(plant_id="TEST_PLANT")
        self.assertEqual(result["mode"], "SIMULATION")
        self.assertEqual(result["plant_id"], "TEST_PLANT")
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["observations"][0]["tag"], "PT-303")
        self.assertEqual(result["observations"][0]["address"], "PIW 260")
        self.assertFalse(result["safety"]["plc_write"])

    def test_missing_tag_is_rejected(self):
        with self.assertRaises(AdapterValidationError):
            normalize_observation({"value": 1.0}, plant_id="P1")

    def test_invalid_quality_is_rejected(self):
        with self.assertRaises(AdapterValidationError):
            normalize_observation(
                {"tag": "PT-1", "value": 1.0, "quality": "UNKNOWN"},
                plant_id="P1",
            )

    def test_live_is_not_enabled_by_default(self):
        result = validate_live_enablement({"protocol": "S7", "enabled": False})
        self.assertFalse(result["ready"])
        self.assertFalse(result["safety"]["plc_write"])

    def test_live_requires_endpoint_and_plant(self):
        with self.assertRaises(AdapterValidationError):
            validate_live_enablement({"protocol": "S7", "enabled": True, "plant_id": "P1"})


if __name__ == "__main__":
    unittest.main()
