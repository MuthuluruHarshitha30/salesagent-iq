"""
REST API Route and Handler Tests.
Tests endpoint status codes, JSON responses, schema exposure,
and query execution handling.
"""

import json
import unittest
from starlette.requests import Request
from src.api.routes import health_check, get_schema, get_summary, process_query_core, serve_index


class TestAPIEndpoints(unittest.TestCase):
    def test_health_endpoint(self):
        """GET /api/health returns 200 and healthy status."""
        res = health_check(None)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode("utf-8"))
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["total_records"], 51)

    def test_schema_endpoint(self):
        """GET /api/schema returns schema, values, and rules."""
        res = get_schema(None)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode("utf-8"))
        self.assertIn("schema", data)
        self.assertIn("categorical_values", data)
        self.assertIn("business_rules", data)

    def test_summary_endpoint(self):
        """GET /api/summary returns dataset KPIs."""
        res = get_summary(None)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode("utf-8"))
        self.assertIn("dataset_overview", data)
        self.assertEqual(data["dataset_overview"]["total_rows"], 51)
        self.assertAlmostEqual(data["dataset_overview"]["total_net_revenue"], 1445200.0, places=2)

    def test_query_endpoint_valid_question(self):
        """POST /api/query with valid question returns structured answer."""
        res = process_query_core({"question": "What is the total revenue?"})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.body.decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertIn("1,445,200.00", data["data"]["summary"])
        self.assertEqual(data["data"]["row_count"], 1)

    def test_query_endpoint_empty_question(self):
        """POST /api/query with empty question returns 400."""
        res = process_query_core({"question": ""})
        self.assertEqual(res.status_code, 400)

    def test_query_endpoint_invalid_body(self):
        """POST /api/query with non-dict body returns 400."""
        res = process_query_core("not a json dict")
        self.assertEqual(res.status_code, 400)

    def test_serve_ui_index(self):
        """GET / returns HTML dashboard."""
        res = serve_index(None)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Mini AI Business Intelligence Assistant", res.body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
