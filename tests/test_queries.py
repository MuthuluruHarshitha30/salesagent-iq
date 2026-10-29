"""
Integration tests for Analytics Engine and Natural Language Queries.
Validates the 5 mandatory example questions plus dynamic multi-filter queries.
"""

import unittest
from src.analytics.engine import AnalyticsEngine


class TestAnalyticsQueries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = AnalyticsEngine()

    def test_question_1_total_revenue(self):
        """Core Question 1: What is the total revenue?"""
        res = self.engine.process_question("What is the total revenue?")
        self.assertEqual(res["intent"], "TOTAL_METRIC")
        self.assertIn("1,445,200.00", res["summary"])
        self.assertEqual(res["row_count"], 1)
        self.assertAlmostEqual(res["supporting_data"][0]["total_net_revenue"], 1445200.0, places=2)

    def test_question_2_highest_revenue_product(self):
        """Core Question 2: Which product generated the highest revenue?"""
        res = self.engine.process_question("Which product generated the highest revenue?")
        self.assertIn("Monitor", res["summary"])
        self.assertIn("473,000.00", res["summary"])
        self.assertEqual(res["supporting_data"][0]["product"], "Monitor")
        self.assertAlmostEqual(res["supporting_data"][0]["total_net_revenue"], 473000.0, places=2)

    def test_question_3_monthly_revenue_trend(self):
        """Core Question 3: What is the monthly revenue trend?"""
        res = self.engine.process_question("What is the monthly revenue trend?")
        self.assertEqual(res["row_count"], 6)
        # Check all 6 months are represented chronologically
        months = [r["month"] for r in res["supporting_data"]]
        self.assertEqual(months, ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])
        # Peak month May (2026-05) has 318,500
        self.assertIn("2026-05", res["summary"])
        self.assertIn("318,500.00", res["summary"])

    def test_question_4_highest_sales_region(self):
        """Core Question 4: Which region generated the highest sales?"""
        res = self.engine.process_question("Which region generated the highest sales?")
        self.assertIn("South", res["summary"])
        self.assertIn("411,200.00", res["summary"])
        self.assertEqual(res["supporting_data"][0]["region"], "South")
        self.assertAlmostEqual(res["supporting_data"][0]["total_net_revenue"], 411200.0, places=2)

    def test_question_5_revenue_change_between_months(self):
        """Core Question 5: How did revenue change between two months?"""
        res = self.engine.process_question("How did revenue change between January and February?")
        self.assertEqual(res["intent"], "COMPARISON")
        comp = res["comparative_metrics"]
        self.assertIsNotNone(comp)
        self.assertAlmostEqual(comp["absolute_difference"], 24350.0, places=2)
        self.assertAlmostEqual(comp["percentage_change"], 11.58, places=2)
        self.assertEqual(comp["direction"], "increased")
        self.assertIn("increased by $24,350.00 (11.58%)", res["summary"])

    def test_dynamic_query_filtered_units(self):
        """Dynamic Ad-hoc Question: How many units of Office Chair were sold in South region?"""
        res = self.engine.process_question("How many units of Office Chair were sold in South region?")
        self.assertEqual(res["row_count"], 1)
        self.assertEqual(res["supporting_data"][0]["total_units_sold"], 10)
        self.assertIn("10", res["summary"])

    def test_dynamic_query_category_discount(self):
        """Dynamic Ad-hoc Question: What is the total discount given in Electronics?"""
        res = self.engine.process_question("What is the total discount given in Electronics?")
        self.assertEqual(res["row_count"], 1)
        # TXN0004 ($500), TXN0012 ($1000), TXN0028 ($500) = $2,000.00
        self.assertAlmostEqual(res["supporting_data"][0]["total_discount"], 2000.0, places=2)
        self.assertIn("2,000.00", res["summary"])

    def test_dynamic_query_channel_comparison(self):
        """Dynamic Ad-hoc Question: Compare online and retail sales"""
        res = self.engine.process_question("Compare online and retail sales")
        self.assertEqual(res["intent"], "COMPARISON")
        self.assertEqual(res["row_count"], 2)

    def test_distinct_products_listing(self):
        """Dynamic Ad-hoc Question: What are the different products?"""
        res = self.engine.process_question("what are the different products")
        self.assertEqual(res["intent"], "ENTITY_LIST")
        self.assertEqual(res["row_count"], 7)
        self.assertIn("7 distinct products", res["summary"])
        self.assertIn("Monitor", res["summary"])
        self.assertIn("Wireless Mouse", res["summary"])

    def test_distinct_categories_listing(self):
        """Dynamic Ad-hoc Question: What are the categories?"""
        res = self.engine.process_question("what are the categories")
        self.assertEqual(res["intent"], "ENTITY_LIST")
        self.assertEqual(res["row_count"], 3)
        self.assertIn("3 distinct categories", res["summary"])
        self.assertIn("Accessories", res["summary"])
        self.assertIn("Furniture", res["summary"])
        self.assertIn("Electronics", res["summary"])


if __name__ == "__main__":
    unittest.main()
