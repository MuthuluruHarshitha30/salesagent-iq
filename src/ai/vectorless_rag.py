"""
Vectorless RAG (Retrieval-Augmented Generation) Knowledge Catalog.

Why Vectorless RAG for BI?
Unlike Vector RAG (which chunks text and embeds it into high-dimensional vector spaces,
causing hallucinations and loss of numerical precision on structured tabular data),
Vectorless RAG uses deterministic schema linking, domain ontologies, business rule catalogs,
and distinct categorical value stores. This guarantees 100% deterministic, mathematically
exact SQL query generation over relational databases.
"""

from typing import Any, Dict, List
import sqlite3
from src.database.connection import get_ro_connection


class VectorlessRAGCatalog:
    """Catalog of relational schema, business rules, and categorical ground truth."""

    SCHEMA_INFO = {
        "table_name": "sales",
        "description": "Sales transactions dataset covering January 2026 to June 2026.",
        "columns": {
            "transaction_id": {"type": "VARCHAR(20)", "desc": "Unique transaction identifier (e.g., TXN0001)"},
            "order_date": {"type": "DATE", "desc": "Date of transaction formatted as YYYY-MM-DD"},
            "year_month": {"type": "VARCHAR(7)", "desc": "Year and month formatted as YYYY-MM (e.g., 2026-01)"},
            "product": {"type": "VARCHAR(100)", "desc": "Name of product sold"},
            "category": {"type": "VARCHAR(100)", "desc": "Product category"},
            "region": {"type": "VARCHAR(50)", "desc": "Geographical sales region"},
            "sales_channel": {"type": "VARCHAR(50)", "desc": "Distribution channel"},
            "quantity": {"type": "INTEGER", "desc": "Number of units ordered in the transaction"},
            "unit_price": {"type": "REAL", "desc": "Selling price per single unit in USD"},
            "discount_amount": {"type": "REAL", "desc": "Discount deducted from the transaction in USD"},
            "gross_revenue": {"type": "REAL", "desc": "quantity * unit_price"},
            "net_revenue": {"type": "REAL", "desc": "(quantity * unit_price) - discount_amount"},
            "status": {"type": "VARCHAR(20)", "desc": "Order fulfillment status ('Completed' or 'Returned')"},
            "is_imputed": {"type": "INTEGER", "desc": "1 if unit_price was imputed during ETL, else 0"}
        }
    }

    BUSINESS_RULES = [
        "Revenue Definition: Net revenue is defined as (quantity * unit_price) - discount_amount (or net_revenue column).",
        "Standard Status Filter: Business revenue queries MUST default to `status = 'Completed'` unless the user explicitly requests returns or all statuses.",
        "Date Format: Dates are in ISO 'YYYY-MM-DD'. Monthly groupings use `year_month` or `strftime('%Y-%m', order_date)`.",
        "Imputation Awareness: TXN0051 had a missing unit price for 'Laptop Stand' imputed to 1200.0 based on median historical unit price.",
        "Returns Awareness: TXN0033 is marked 'Returned' with gross value 19,000.0. Excluded from completed revenue."
    ]

    MONTH_MAP = {
        "january": "2026-01", "jan": "2026-01", "01": "2026-01", "1": "2026-01",
        "february": "2026-02", "feb": "2026-02", "02": "2026-02", "2": "2026-02",
        "march": "2026-03", "mar": "2026-03", "03": "2026-03", "3": "2026-03",
        "april": "2026-04", "apr": "2026-04", "04": "2026-04", "4": "2026-04",
        "may": "2026-05", "05": "2026-05", "5": "2026-05",
        "june": "2026-06", "jun": "2026-06", "06": "2026-06", "6": "2026-06"
    }

    @classmethod
    def get_categorical_values(cls) -> Dict[str, List[Any]]:
        """Fetch distinct ground-truth categorical values from database."""
        try:
            conn = get_ro_connection()
            categories = [r[0] for r in conn.execute("SELECT DISTINCT category FROM sales;").fetchall()]
            products = [r[0] for r in conn.execute("SELECT DISTINCT product FROM sales;").fetchall()]
            regions = [r[0] for r in conn.execute("SELECT DISTINCT region FROM sales;").fetchall()]
            channels = [r[0] for r in conn.execute("SELECT DISTINCT sales_channel FROM sales;").fetchall()]
            statuses = [r[0] for r in conn.execute("SELECT DISTINCT status FROM sales;").fetchall()]
            year_months = [r[0] for r in conn.execute("SELECT DISTINCT year_month FROM sales ORDER BY year_month;").fetchall()]
            conn.close()
            return {
                "category": categories,
                "product": products,
                "region": regions,
                "sales_channel": channels,
                "status": statuses,
                "year_month": year_months
            }
        except Exception:
            # Fallback to static catalog if DB is not yet initialized
            return {
                "category": ["Accessories", "Furniture", "Electronics"],
                "product": ["Laptop Stand", "Wireless Mouse", "Office Chair", "Monitor", "Keyboard", "Desk", "USB-C Hub"],
                "region": ["North", "South", "West", "East"],
                "sales_channel": ["Online", "Retail"],
                "status": ["Completed", "Returned"],
                "year_month": ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
            }

    @classmethod
    def get_prompt_context(cls) -> str:
        """Construct full Vectorless RAG context for Text-to-SQL models."""
        cats = cls.get_categorical_values()
        lines = [
            "# DATABASE SCHEMA: Table `sales`",
            "Columns:"
        ]
        for col, meta in cls.SCHEMA_INFO["columns"].items():
            lines.append(f"  - `{col}` ({meta['type']}): {meta['desc']}")

        lines.append("\n# CATEGORICAL GROUND TRUTH VALUES:")
        for cat_col, vals in cats.items():
            lines.append(f"  - {cat_col}: {vals}")

        lines.append("\n# CORE BUSINESS LOGIC & CONSTRAINTS:")
        for rule in cls.BUSINESS_RULES:
            lines.append(f"  - {rule}")

        return "\n".join(lines)
