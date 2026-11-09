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
