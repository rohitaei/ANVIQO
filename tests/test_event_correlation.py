import unittest

from event_correlation import correlate_events


class TestUniversalEventCorrelation(unittest.TestCase):
    def test_arbitrary_equipment_and_event_types_are_correlated_without_process_rules(self):
        events = [
            {
                "timestamp": "2026-09-25T01:00:00",
                "event_type": "SENSOR_STATE_CHANGE",
                "equipment": "EQ-901",
                "message": "Signal changed from normal to warning.",
            },
            {
                "timestamp": "2026-09-25T01:02:00",
                "event_type": "MAINTENANCE_EVENT",
                "equipment": "EQ-901",
                "message": "Inspection recorded.",
            },
        ]
        result = correlate_events("EQ-901", events)
        self.assertEqual(result["status"], "MULTIPLE EVENTS")
        self.assertEqual(result["event_count"], 2)
        self.assertEqual(result["event_types"], ["SENSOR_STATE_CHANGE", "MAINTENANCE_EVENT"])
        self.assertFalse(result["causation_claimed"])
        self.assertEqual(result["chain"][0]["equipment"], "EQ-901")

    def test_different_equipment_is_not_mixed(self):
        events = [
            {"timestamp": "2026-09-25T01:00:00", "event_type": "A", "equipment": "EQ-1", "message": "A"},
            {"timestamp": "2026-09-25T01:01:00", "event_type": "B", "equipment": "EQ-2", "message": "B"},
        ]
        result = correlate_events("EQ-1", events)
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(result["chain"][0]["equipment"], "EQ-1")

    def test_empty_events_are_safe(self):
        result = correlate_events("ANY-TAG", [])
        self.assertEqual(result["status"], "NO DATA")
        self.assertFalse(result["causation_claimed"])


if __name__ == "__main__":
    unittest.main()
