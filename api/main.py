"""FastAPI application entry point with lifespan management."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware import RequestLoggingMiddleware
from api.models import HealthResponse
from api.routes import analytics, brands, compare, ingest, insights, pipeline, runs, signals, trends
from db.connection import close_pool, create_pool, get_pool
from pipeline.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up — connecting to database...")
    await create_pool()
    logger.info("Database pool ready")
    yield
    logger.info("Shutting down — closing database pool...")
    await close_pool()


app = FastAPI(
    title="Social Media Decoded",
    description="Multi-agent social signal intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(pipeline.router)
app.include_router(insights.router)
app.include_router(brands.router)
app.include_router(runs.router)
app.include_router(trends.router)
app.include_router(signals.router)
app.include_router(compare.router)
app.include_router(analytics.router)


@app.get("/metrics", tags=["system"], response_class=None)
async def metrics_endpoint():
    """Prometheus-compatible metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    from pipeline.metrics import get_registry
    return PlainTextResponse(get_registry().to_prometheus(), media_type="text/plain")


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Liveness + readiness probe."""
    db_ok = False
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db=db_ok,
    )
