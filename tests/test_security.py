"""
Security & Guardrails Tests.
Verifies that destructive queries, SQL injections, and unauthorized
database access attempts are strictly blocked.
"""

import unittest
from src.ai.sql_guardrails import SQLGuardrails, SQLSecurityError


class TestSQLSecurityGuardrails(unittest.TestCase):
    def test_block_drop_table(self):
        """Reject DROP TABLE command."""
        with self.assertRaises(SQLSecurityError):
            SQLGuardrails.validate_query("DROP TABLE sales;")

    def test_block_delete(self):
        """Reject DELETE command."""
        with self.assertRaises(SQLSecurityError):
            SQLGuardrails.validate_query("DELETE FROM sales WHERE quantity > 0;")

    def test_block_update(self):
        """Reject UPDATE command."""
        with self.assertRaises(SQLSecurityError):
            SQLGuardrails.validate_query("UPDATE sales SET unit_price = 0;")

    def test_block_insert(self):
        """Reject INSERT command."""
        with self.assertRaises(SQLSecurityError):
            SQLGuardrails.validate_query("INSERT INTO sales (transaction_id) VALUES ('HACK');")

    def test_block_alter_table(self):
        """Reject ALTER TABLE command."""
        with self.assertRaises(SQLSecurityError):
            SQLGuardrails.validate_query("ALTER TABLE sales ADD COLUMN pwned TEXT;")

    def test_block_stacked_queries_injection(self):
        """Reject semicolon stacked query injection."""
        with self.assertRaises(SQLSecurityError):
            SQLGuardrails.validate_query("SELECT * FROM sales; DROP TABLE sales;")

    def test_block_unauthorized_table(self):
        """Reject queries accessing non-allowed tables."""
        with self.assertRaises(SQLSecurityError):
            SQLGuardrails.validate_query("SELECT * FROM sqlite_master;")

    def test_allow_safe_select(self):
        """Allow valid, safe read-only SELECT query."""
        report = SQLGuardrails.validate_query("SELECT product, SUM(net_revenue) FROM sales GROUP BY product;")
        self.assertTrue(report["is_safe"])
        self.assertTrue(report["read_only"])


if __name__ == "__main__":
    unittest.main()
