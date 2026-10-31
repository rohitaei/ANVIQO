import unittest

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


if __name__ == "__main__":
    unittest.main()
