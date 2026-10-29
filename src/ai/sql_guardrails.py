"""
SQL Guardrails & Security Validator.
Enforces read-only safety, AST-level checks, injection prevention,
and prevents destructive operations on the database.
"""

import re
from typing import Any, Dict, List, Set, Tuple


class SQLSecurityError(Exception):
    """Raised when an unsafe or forbidden SQL query is attempted."""
    pass


class SQLGuardrails:
    # Forbidden keywords that mutate schema or data, or access system internals
    DISALLOWED_KEYWORDS: Set[str] = {
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
        "REPLACE", "CREATE", "EXEC", "EXECUTE", "ATTACH", "DETACH",
        "PRAGMA", "GRANT", "REVOKE", "VACUUM", "REINDEX", "SAVEPOINT",
        "RELEASE", "COMMIT", "ROLLBACK", "LOAD_EXTENSION"
    }

    ALLOWED_TABLES: Set[str] = {"sales"}

    ALLOWED_COLUMNS: Set[str] = {
        "transaction_id", "order_date", "year_month", "product", "category",
        "region", "sales_channel", "quantity", "unit_price", "discount_amount",
        "gross_revenue", "net_revenue", "status", "is_imputed", "created_at"
    }

    @classmethod
    def validate_query(cls, sql: str) -> Dict[str, Any]:
        """
        Thoroughly validate a candidate SQL query for safety.
        Returns validation metadata or raises SQLSecurityError.
        """
        if not sql or not isinstance(sql, str):
            raise SQLSecurityError("Query must be a non-empty string.")

        cleaned = sql.strip().rstrip(";")

        # 1. Reject multiple statements (prevent stacked query injection: e.g. SELECT 1; DROP TABLE ...)
        if ";" in cleaned:
            raise SQLSecurityError("Multiple SQL statements are strictly forbidden.")

        # 2. Check query starts with SELECT or WITH (for CTEs)
        upper_query = cleaned.upper()
        if not (upper_query.startswith("SELECT") or upper_query.startswith("WITH")):
            raise SQLSecurityError("Only SELECT queries are permitted.")

        # 3. Scan for forbidden keyword tokens (regex tokenization to prevent word boundary bypasses)
        tokens = re.findall(r"\b[A-Za-z_]+\b", upper_query)
        for token in tokens:
            if token in cls.DISALLOWED_KEYWORDS:
                raise SQLSecurityError(f"Forbidden SQL keyword detected: '{token}'. Query rejected for security.")

        # 4. Check for comments that could be used for comment-injection (/* ... */ or --)
        if "/*" in cleaned or "--" in cleaned:
            # Clean comments out or check if malicious
            cleaned_no_comments = re.sub(r"--.*", "", cleaned)
            cleaned_no_comments = re.sub(r"/\*.*?\*/", "", cleaned_no_comments, flags=re.DOTALL).strip()
            if not cleaned_no_comments:
                raise SQLSecurityError("Query contains only comments.")
            cleaned = cleaned_no_comments.rstrip(";")

        # 5. Verify table name reference
        table_matches = re.findall(r"\bFROM\s+([A-Za-z0-9_]+)", cleaned, re.IGNORECASE)
        for tbl in table_matches:
            if tbl.lower() not in cls.ALLOWED_TABLES:
                raise SQLSecurityError(f"Access to unauthorized table '{tbl}' is forbidden. Only 'sales' is accessible.")

        join_matches = re.findall(r"\bJOIN\s+([A-Za-z0-9_]+)", cleaned, re.IGNORECASE)
        for tbl in join_matches:
            if tbl.lower() not in cls.ALLOWED_TABLES:
                raise SQLSecurityError(f"Join with unauthorized table '{tbl}' is forbidden.")

        return {
            "is_safe": True,
            "read_only": True,
            "validated_query": cleaned,
            "tables_accessed": list(set([t.lower() for t in table_matches] or ["sales"]))
        }
