"""
Unit tests for ETL Pipeline and Data Cleansing.
"""

import unittest
from pathlib import Path
from src.database.connection import get_ro_connection
from src.database.etl import SalesETLPipeline


class TestETLPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pipeline = SalesETLPipeline()
        cls.report = pipeline.run()

    def test_total_row_count(self):
        """Ensure all 51 raw rows from the source CSV are loaded."""
        self.assertEqual(self.report["total_processed_rows"], 51)
        self.assertEqual(self.report["completed_transactions"], 50)
        self.assertEqual(self.report["returned_transactions"], 1)

    def test_missing_unit_price_imputation(self):
        """
        Verify edge case TXN0051: missing unit_price for Laptop Stand
        is imputed to 1200.0 using the historical median.
        """
        conn = get_ro_connection()
        row = conn.execute("SELECT unit_price, is_imputed, net_revenue FROM sales WHERE transaction_id = 'TXN0051';").fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row["unit_price"], 1200.0)
        self.assertEqual(row["is_imputed"], 1)
        # Quantity 5 * 1200 - 0 discount = 6000.0
        self.assertEqual(row["net_revenue"], 6000.0)

    def test_iso_date_standardization(self):
        """Verify date conversion from DD-MM-YYYY to ISO YYYY-MM-DD and year_month."""
        conn = get_ro_connection()
        row = conn.execute("SELECT order_date, year_month FROM sales WHERE transaction_id = 'TXN0001';").fetchone()
        conn.close()

        self.assertEqual(row["order_date"], "2026-01-03")
        self.assertEqual(row["year_month"], "2026-01")

    def test_total_completed_net_revenue(self):
        """Verify mathematically exact net revenue calculation across all completed orders."""
        conn = get_ro_connection()
        row = conn.execute("SELECT SUM(net_revenue) AS total FROM sales WHERE status = 'Completed';").fetchone()
        conn.close()

        self.assertAlmostEqual(row["total"], 1445200.0, places=2)

    def test_returned_order_isolation(self):
        """Verify TXN0033 is correctly tagged as 'Returned'."""
        conn = get_ro_connection()
        row = conn.execute("SELECT status, gross_revenue FROM sales WHERE transaction_id = 'TXN0033';").fetchone()
        conn.close()

        self.assertEqual(row["status"], "Returned")
        self.assertEqual(row["gross_revenue"], 19000.0)


if __name__ == "__main__":
    unittest.main()
