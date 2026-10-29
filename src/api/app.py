"""
Main ASGI application for Mini AI Business Intelligence Assistant.
Configured with Starlette and Uvicorn.
"""

from pathlib import Path
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from src.api.routes import health_check, get_schema, get_summary, process_query, serve_index
from src.database.connection import get_db_path
from src.database.etl import SalesETLPipeline

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "src" / "ui" / "static"


def create_app() -> Starlette:
    # Ensure database exists
    db_file = get_db_path()
    if not db_file.exists():
        print("[App Init] Database not found. Running initial ETL pipeline...")
        pipeline = SalesETLPipeline()
        pipeline.run()
        print("[App Init] ETL pipeline finished successfully.")

    routes = [
        Route("/", endpoint=serve_index, methods=["GET"]),
        Route("/api/health", endpoint=health_check, methods=["GET"]),
        Route("/api/schema", endpoint=get_schema, methods=["GET"]),
        Route("/api/summary", endpoint=get_summary, methods=["GET"]),
        Route("/api/query", endpoint=process_query, methods=["POST"]),
        Mount("/static", app=StaticFiles(directory=str(STATIC_DIR)), name="static")
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"]
        )
    ]

    app = Starlette(debug=True, routes=routes, middleware=middleware)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    print("Starting Mini AI BI Assistant on http://127.0.0.1:8000")
    uvicorn.run("src.api.app:app", host="127.0.0.1", port=8000, reload=False)
