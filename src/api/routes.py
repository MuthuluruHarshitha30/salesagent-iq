"""
API Routes and Handlers for the BI Assistant.
Provides endpoints for query processing, schema exploration,
dataset summary, and health checks.
"""

import json
from pathlib import Path
from typing import Any, Dict

from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from starlette.staticfiles import StaticFiles

from src.ai.sql_guardrails import SQLSecurityError
from src.ai.vectorless_rag import VectorlessRAGCatalog
from src.analytics.engine import AnalyticsEngine
from src.database.connection import get_ro_connection

STATIC_DIR = Path(__file__).resolve().parent.parent / "ui" / "static"
analytics_engine = AnalyticsEngine()


def health_check(request: Request) -> JSONResponse:
    """Check API and database health status."""
    try:
        conn = get_ro_connection()
        row = conn.execute("SELECT COUNT(*) FROM sales;").fetchone()
        count = row[0] if row else 0
        conn.close()
        return JSONResponse({
            "status": "healthy",
            "database": "connected",
            "total_records": count,
            "version": "1.0.0"
        })
    except Exception as e:
        return JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=500)


def get_schema(request: Request) -> JSONResponse:
    """Return database schema, categorical values, and business rules (Vectorless RAG)."""
    return JSONResponse({
        "schema": VectorlessRAGCatalog.SCHEMA_INFO,
        "categorical_values": VectorlessRAGCatalog.get_categorical_values(),
        "business_rules": VectorlessRAGCatalog.BUSINESS_RULES
    })


def get_summary(request: Request) -> JSONResponse:
    """Return high-level summary statistics of the dataset."""
    try:
        conn = get_ro_connection()
        
        # Summary metrics
        total_q = """
            SELECT 
                COUNT(*) AS total_rows,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_orders,
                SUM(CASE WHEN status = 'Returned' THEN 1 ELSE 0 END) AS returned_orders,
                SUM(CASE WHEN status = 'Completed' THEN net_revenue ELSE 0 END) AS total_net_revenue,
                SUM(CASE WHEN status = 'Completed' THEN gross_revenue ELSE 0 END) AS total_gross_revenue,
                SUM(CASE WHEN status = 'Completed' THEN discount_amount ELSE 0 END) AS total_discounts,
                SUM(CASE WHEN status = 'Completed' THEN quantity ELSE 0 END) AS total_units,
                MIN(order_date) AS min_date,
                MAX(order_date) AS max_date
            FROM sales;
        """
        row = dict(conn.execute(total_q).fetchone())

        # Top product
        top_prod_row = dict(conn.execute("""
            SELECT product, SUM(net_revenue) AS revenue 
            FROM sales WHERE status = 'Completed' 
            GROUP BY product ORDER BY revenue DESC LIMIT 1;
        """).fetchone())

        # Top region
        top_reg_row = dict(conn.execute("""
            SELECT region, SUM(net_revenue) AS revenue 
            FROM sales WHERE status = 'Completed' 
            GROUP BY region ORDER BY revenue DESC LIMIT 1;
        """).fetchone())

        conn.close()

        return JSONResponse({
            "dataset_overview": row,
            "top_product": top_prod_row,
            "top_region": top_reg_row
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def process_query_core(body: Any) -> JSONResponse:
    """Core logic for question processing, decoupled from async transport for testing."""
    if not isinstance(body, dict):
        return JSONResponse(
            {"error": "Invalid request body. Expected JSON object with a 'question' field."},
            status_code=400
        )

    question = body.get("question", "").strip() if isinstance(body.get("question"), str) else ""
    if not question:
        return JSONResponse(
            {"error": "Missing or empty 'question' field."},
            status_code=400
        )

    try:
        result = analytics_engine.process_question(question)
        return JSONResponse({
            "success": True,
            "data": result
        })
    except SQLSecurityError as sec_err:
        return JSONResponse({
            "success": False,
            "error_type": "SecurityGuardrailViolation",
            "error": str(sec_err)
        }, status_code=403)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error_type": "ExecutionError",
            "error": str(e)
        }, status_code=500)


async def process_query(request: Request) -> JSONResponse:
    """
    Accepts natural language question, processes via AI/Vectorless RAG + SQL Guardrails,
    and returns structured answer with supporting figures.
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"error": "Invalid request body. Expected JSON with a 'question' field."},
            status_code=400
        )

    return process_query_core(body)


def serve_index(request: Request) -> HTMLResponse:
    """Serve the modern web dashboard interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content)
    return HTMLResponse("<h1>Mini BI Assistant UI Not Found</h1>", status_code=404)
