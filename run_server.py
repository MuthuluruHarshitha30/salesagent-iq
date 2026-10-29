"""
One-click entry point to start the SalesAgent IQ server.
Usage: python run_server.py [--port 8000] [--host 127.0.0.1]
"""

import argparse
import sys
from pathlib import Path
import uvicorn

# Ensure project root is in path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.database.connection import get_db_path
from src.database.etl import SalesETLPipeline


def main():
    parser = argparse.ArgumentParser(description="Run SalesAgent IQ Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    args = parser.parse_args()

    # Check and run initial ETL if needed
    db_file = get_db_path()
    if not db_file.exists():
        print("[System] Database not found. Executing ETL pipeline...")
        pipeline = SalesETLPipeline()
        pipeline.run()
        print("[System] ETL pipeline finished.")

    print("=" * 65)
    print("🤖 SalesAgent IQ is running!")
    print(f"👉 Web Dashboard:    http://{args.host}:{args.port}")
    print(f"👉 API Health Check: http://{args.host}:{args.port}/api/health")
    print(f"👉 Schema & Rules:   http://{args.host}:{args.port}/api/schema")
    print("=" * 65)

    uvicorn.run("src.api.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
