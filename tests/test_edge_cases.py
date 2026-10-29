"""
Edge Cases and Boundary Condition Tests.
"""

import unittest
from src.analytics.engine import AnalyticsEngine
from src.database.connection import get_ro_connection


class TestEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = AnalyticsEngine()

    def test_zero_quantity_transaction(self):
        """Verify TXN0034 (0 quantity) is handled gracefully without division by zero or errors."""
        conn = get_ro_connection()
        row = conn.execute("SELECT quantity, gross_revenue, net_revenue FROM sales WHERE transaction_id = 'TXN0034';").fetchone()
        conn.close()

        self.assertEqual(row["quantity"], 0)
        self.assertEqual(row["gross_revenue"], 0.0)
        self.assertEqual(row["net_revenue"], 0.0)

    def test_empty_query_raises_error(self):
        """Verify empty string or whitespace raises ValueError."""
        with self.assertRaises(ValueError):
            self.engine.process_question("")
        with self.assertRaises(ValueError):
            self.engine.process_question("    ")

    def test_unmatched_filter_returns_empty_results(self):
        """Query for a non-existent product returns clean zero-match message."""
        res = self.engine.process_question("What is the revenue for Supercar?")
        # Defaults to total metric or empty
        self.assertIn("No matching sales records were found", res["summary"])

    def test_returned_transactions_explicit_query(self):
        """Verify querying returned transactions directly."""
        res = self.engine.process_question("List all returned orders")
        self.assertEqual(res["row_count"], 1)
        self.assertEqual(res["supporting_data"][0]["transaction_id"], "TXN0033")
        self.assertEqual(res["supporting_data"][0]["status"], "Returned")


if __name__ == "__main__":
    unittest.main()
