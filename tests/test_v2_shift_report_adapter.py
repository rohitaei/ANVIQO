import unittest

from v2.shift_report_adapter import ShiftReportSourceAdapter, parse_shift_report_text


REPORT = """TATA METALIKS LTD.
KHARAGPUR.
SHIFT METRIAL REPORT FOR VARIOUS BIN
DATE\t9/23/2026
 1 Hr. Avg. Value\tPT_301\tPT_302\tPT_303\tPT_304\tTE_301
00:00Hrs - 1:00Hrs\t7.355323792\t7.306134224\t7.333333492\t0.0802083388\t40.60000229
1:00Hrs - 2:00Hrs\t7.410300732\t7.199073792\t6.837384224\t5.324073792\t40.90000153
2:00Hrs - 3:00Hrs\t7.306134224\t7.459490299\t6.736110687\t1.171875\t41.20000076
"""


class TestShiftReportAdapter(unittest.TestCase):
    def test_alpha30_normalizes_real_report_shape(self):
        points = list(parse_shift_report_text(REPORT, plant_id="PLANT-A"))
        self.assertEqual(len(points), 15)

        pt303 = [p for p in points if p.tag == "PT_303"]
        self.assertEqual(len(pt303), 3)
        self.assertEqual(pt303[0].value, 7.333333492)
        self.assertEqual(pt303[0].timestamp, "2026-09-23T00:00:00+00:00")
        self.assertEqual(pt303[1].timestamp, "2026-09-23T01:00:00+00:00")
        self.assertEqual(pt303[2].timestamp, "2026-09-23T02:00:00+00:00")
        self.assertTrue(all(p.plant_id == "PLANT-A" for p in points))
        self.assertTrue(all(p.source == "TATA METALIKS SHIFT MATERIAL REPORT" for p in points))
        self.assertTrue(all(p.mode == "HISTORICAL" for p in points))

    def test_alpha30_blank_and_non_numeric_cells_are_not_invented(self):
        report = """DATE\t9/23/2026
 1 Hr. Avg. Value\tPT_303\tPT_304\tEMPTY
00:00Hrs - 1:00Hrs\t7.3\t\tN/A
"""
        points = list(parse_shift_report_text(report, plant_id="PLANT-A"))
        self.assertEqual([(p.tag, p.value) for p in points], [("PT_303", 7.3)])

    def test_alpha30_requires_plant_scope(self):
        with self.assertRaisesRegex(ValueError, "plant_id"):
            list(parse_shift_report_text(REPORT, plant_id=""))

    def test_alpha30_preserves_report_as_historical_not_live(self):
        points = list(parse_shift_report_text(REPORT, plant_id="PLANT-A"))
        self.assertTrue(all(p.mode == "HISTORICAL" for p in points))
        self.assertTrue(all(p.quality == "UNKNOWN" for p in points))

    def test_alpha30_source_adapter_uses_supplied_tenant(self):
        adapter = ShiftReportSourceAdapter(REPORT, name="TATA METALIKS REPORT")
        points = list(adapter.read("PLANT-B"))
        self.assertEqual(len(points), 15)
        self.assertTrue(all(p.plant_id == "PLANT-B" for p in points))
        self.assertTrue(all(p.source == "TATA METALIKS REPORT" for p in points))


if __name__ == "__main__":
    unittest.main()
