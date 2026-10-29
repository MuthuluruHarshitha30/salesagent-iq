"""
Database connection management.
Provides read-write connection for ETL and read-only connection for analytics queries.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "sales.db"


def get_db_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def get_rw_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a read-write database connection (used for ETL and initialization)."""
    target = db_path or get_db_path()
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_ro_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Get a strictly read-only database connection using SQLite URI mode.
    Guarantees OS-level defense-in-depth against write or destructive operations.
    """
    target = db_path or get_db_path()
    if not target.exists():
        raise FileNotFoundError(f"Database not found at {target}. Run ETL pipeline first.")
    
    # SQLite read-only URI
    uri = f"file:{target.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn
