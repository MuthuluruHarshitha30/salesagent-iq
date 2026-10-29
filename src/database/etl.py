"""
ETL Pipeline for Mini AI Business Intelligence Assistant.
Loads raw sales CSV, performs automated data cleansing, validation,
and imputation, stores processed data in SQLite, and exports an audit report.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.database.connection import get_db_path, get_rw_connection


class SalesETLPipeline:
    def __init__(self, csv_path: Optional[Path] = None, db_path: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.csv_path = csv_path or (base_dir / "data" / "sales_transactions.csv")
        self.db_path = db_path or get_db_path()
        self.schema_path = Path(__file__).resolve().parent / "schema.sql"
        self.report_path = (base_dir / "data" / "data_cleaning_report.json")
        self.cleaning_log: List[Dict[str, Any]] = []

    def run(self) -> Dict[str, Any]:
        """Execute full ETL process and return summary."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Source CSV not found: {self.csv_path}")

        # 1. Read raw CSV
        df = pd.read_csv(self.csv_path)
        total_raw_rows = len(df)

        # 2. Clean column names
        df.columns = [c.strip().lower() for c in df.columns]

        # 3. Clean string fields
        str_cols = ["transaction_id", "product", "category", "region", "sales_channel", "status"]
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        # 4. Standardize dates from DD-MM-YYYY to YYYY-MM-DD
        standardized_dates = []
        year_months = []
        for idx, row in df.iterrows():
            raw_date = str(row["order_date"]).strip()
            try:
                dt = datetime.strptime(raw_date, "%d-%m-%Y")
                standardized_dates.append(dt.strftime("%Y-%m-%d"))
                year_months.append(dt.strftime("%Y-%m"))
            except ValueError:
                try:
                    dt = datetime.strptime(raw_date, "%Y-%m-%d")
                    standardized_dates.append(dt.strftime("%Y-%m-%d"))
                    year_months.append(dt.strftime("%Y-%m"))
                except Exception as e:
                    self.cleaning_log.append({
                        "row_index": idx,
                        "transaction_id": row.get("transaction_id"),
                        "issue": "Invalid date format",
                        "raw_value": raw_date,
                        "resolution": "Failed parsing",
                        "error": str(e)
                    })
                    raise ValueError(f"Unparseable date at row {idx}: {raw_date}")

        df["order_date"] = standardized_dates
        df["year_month"] = year_months

        # 5. Clean & Validate Numeric Columns
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
        df["discount_amount"] = pd.to_numeric(df["discount_amount"], errors="coerce").fillna(0.0).astype(float)
        
        # Check Unit Price & Impute missing
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
        df["is_imputed"] = 0

        # Calculate reference price map per product from valid records
        product_price_map = (
            df.dropna(subset=["unit_price"])
            .groupby("product")["unit_price"]
            .median()
            .to_dict()
        )

        imputed_count = 0
        for idx, row in df.iterrows():
            if pd.isna(row["unit_price"]):
                prod = row["product"]
                imputed_val = product_price_map.get(prod, 0.0)
                df.at[idx, "unit_price"] = imputed_val
                df.at[idx, "is_imputed"] = 1
                imputed_count += 1
                self.cleaning_log.append({
                    "row_index": idx,
                    "transaction_id": row["transaction_id"],
                    "issue": "Missing unit_price",
                    "product": prod,
                    "resolution": "Imputed using historical median unit price for product",
                    "imputed_value": float(imputed_val)
                })

        # 6. Compute gross and net revenues
        df["gross_revenue"] = df["quantity"] * df["unit_price"]
        df["net_revenue"] = df["gross_revenue"] - df["discount_amount"]

        # Ensure no negative net revenue
        df["net_revenue"] = df["net_revenue"].apply(lambda v: max(0.0, float(v)))

        # 7. Audit anomalies
        # Flag zero-quantity orders
        zero_qty = df[df["quantity"] == 0]
        for idx, row in zero_qty.iterrows():
            self.cleaning_log.append({
                "row_index": idx,
                "transaction_id": row["transaction_id"],
                "issue": "Zero quantity transaction",
                "resolution": "Preserved in database with zero revenue",
                "details": f"Product: {row['product']}, Status: {row['status']}"
            })

        # Flag returned orders
        returned = df[df["status"].str.lower() == "returned"]
        for idx, row in returned.iterrows():
            self.cleaning_log.append({
                "row_index": idx,
                "transaction_id": row["transaction_id"],
                "issue": "Returned order status",
                "resolution": "Tagged as Returned; analytics queries default to Completed transactions",
                "details": f"Gross amount: {row['gross_revenue']}"
            })

        # 8. Store in SQLite Database
        self._write_to_database(df)

        # 9. Write audit report
        report = {
            "timestamp": datetime.now().isoformat(),
            "source_file": str(self.csv_path),
            "target_database": str(self.db_path),
            "total_raw_rows": total_raw_rows,
            "total_processed_rows": len(df),
            "completed_transactions": int((df["status"] == "Completed").sum()),
            "returned_transactions": int((df["status"] == "Returned").sum()),
            "imputed_records": imputed_count,
            "total_gross_revenue_completed": float(df[df["status"] == "Completed"]["gross_revenue"].sum()),
            "total_net_revenue_completed": float(df[df["status"] == "Completed"]["net_revenue"].sum()),
            "total_discounts_completed": float(df[df["status"] == "Completed"]["discount_amount"].sum()),
            "cleaning_events": self.cleaning_log
        }

        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report

    def _write_to_database(self, df: pd.DataFrame) -> None:
        """Create schema and populate SQLite database."""
        conn = get_rw_connection(self.db_path)
        with open(self.schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with conn:
            conn.executescript(schema_sql)
            # Clear existing data for idempotent re-runs
            conn.execute("DELETE FROM sales;")

            cols = [
                "transaction_id", "order_date", "year_month", "product", "category",
                "region", "sales_channel", "quantity", "unit_price", "discount_amount",
                "gross_revenue", "net_revenue", "status", "is_imputed"
            ]
            
            insert_sql = f"""
                INSERT INTO sales ({', '.join(cols)})
                VALUES ({', '.join(['?'] * len(cols))})
            """
            
            records = df[cols].values.tolist()
            conn.executemany(insert_sql, records)
        
        conn.close()


if __name__ == "__main__":
    pipeline = SalesETLPipeline()
    summary = pipeline.run()
    print("ETL completed successfully!")
    print(f"Total rows processed: {summary['total_processed_rows']}")
    print(f"Total completed net revenue: ${summary['total_net_revenue_completed']:,.2f}")
    print(f"Imputed records: {summary['imputed_records']}")
