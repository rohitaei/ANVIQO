import unittest

from anvi_plant_data_import import _matrix_records
from universal_onboarding import normalize_record

from anvi_tenant_spares import (
    _number, _stock_status, is_low_stock_question, is_spare_question
)


class TenantSpareIntentTests(unittest.TestCase):
    def test_low_stock_hyphenated_intent(self):
        self.assertTrue(is_low_stock_question("Show low-stock critical spares"))

    def test_low_stock_spaced_intent(self):
        self.assertTrue(is_low_stock_question("Show low stock critical spares"))

    def test_spare_intent(self):
        self.assertTrue(is_spare_question("Show critical spares"))

    def test_not_spare_intent(self):
        self.assertFalse(is_spare_question("Show current plant health"))

    def test_quantity_text(self):
        self.assertEqual(_number("3 nos"), 3.0)

    def test_below_required(self):
        self.assertEqual(_stock_status(2, 3), "BELOW REQUIRED")

    def test_zero_stock(self):
        self.assertEqual(_stock_status(0, 1), "ZERO STOCK")

    def test_reorder_level(self):
        self.assertEqual(_stock_status(2, None, 2), "LOW STOCK")

    def test_spares_xlsx_headers_are_detected(self):
        rows = [
            ("SPARES FOR PCI", None, None, None, None),
            ("SL.NO", "INSTRUMENT", "QTY AVBL", "QTY REQ", "TAG NO"),
            (1, "Pressure transmitter", 2, 4, "PT-303"),
        ]
        parsed = list(_matrix_records("PT", rows))
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["record_type"], "CRITICAL_SPARE")
        self.assertEqual(parsed[0]["external_id"], "PT-303")

    def test_spares_record_normalizes_tag_and_keeps_stock_fields(self):
        raw = {
            "record_type": "CRITICAL_SPARE",
            "external_id": "PT-303",
            "TAG NO": "PT-303",
            "INSTRUMENT": "Pressure transmitter",
            "QTY AVBL": 2,
            "QTY REQ": 4,
            "source": "PT",
        }
        record = normalize_record(raw, "CRITICAL_SPARE")
        self.assertEqual(record.tag, "PT-303")
        self.assertEqual(record.name, "Pressure transmitter")
        self.assertEqual(record.metadata["QTY AVBL"], 2)
        self.assertEqual(record.metadata["QTY REQ"], 4)

    def test_generated_workbook_row_id_is_not_displayed_as_equipment_tag(self):
        from unittest.mock import patch
        from anvi_tenant_spares import answer

        row = (
            "Analyser-10", "Analyser", "PCI", "Analyser service", "NA",
            "critical_spares.xlsx",
            {"sheet_name": "Analyser", "workbook_row": 10, "qty_available": 0, "qty_required": 1},
            "critical_spares.xlsx",
        )
        with patch("anvi_tenant_spares._load", return_value=[row]):
            result = answer("Show critical spares inventory", "plant-1", "org-1")

        self.assertEqual(result["records"][0]["tag"], "Tag not recorded (workbook row Analyser #10)")
        self.assertNotIn("Analyser-10 —", result["answer"])

    def test_grouped_source_register_tag_is_preserved(self):
        from unittest.mock import patch
        from anvi_tenant_spares import answer

        grouped_tag = "FSV-506/513/520/527"
        row = (
            grouped_tag, "Flow shutoff valve", "PCI", "FSV group", grouped_tag,
            "critical_spares.xlsx",
            {"sheet_name": "FSV&PCV", "workbook_row": 8, "qty_available": 1, "qty_required": 2},
            "critical_spares.xlsx",
        )
        with patch("anvi_tenant_spares._load", return_value=[row]):
            result = answer("Show critical spares inventory", "plant-1", "org-1")

        self.assertEqual(result["records"][0]["tag"], grouped_tag)


if __name__ == "__main__":
    unittest.main()
