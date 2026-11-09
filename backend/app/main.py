import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router

app = FastAPI(
    title="Blind-Ham Propagation API",
    description="Text-first amateur-radio propagation and space-weather service.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

# The frontend and API are served from the same origin in production.
# CORS is intentionally not opened to arbitrary origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router, prefix="/api/v1")

# Local development serves the same frontend from Uvicorn. Production keeps
# frontend delivery in Apache and proxies only the API to this application.
if os.environ.get("BLIND_HAM_LOCAL_SESSION") == "1":
    from fastapi.staticfiles import StaticFiles

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
