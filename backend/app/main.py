"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import v1_router
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware, setup_logging
from app.db.mongodb import MongoDB

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    setup_logging(log_level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)
    logger.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    # Initialize MongoDB
    try:
        await MongoDB.connect()
        logger.info("MongoDB connected")
    except RuntimeError as exc:
        logger.warning("MongoDB connection failed at startup: %s", exc)

    # Validate Mock Campaign API connectivity (non-blocking — log only)
    mock_status = await settings.validate_mock_api_connection()
    if mock_status["status"] == "ok":
        logger.info("Mock Campaign API reachable (HTTP %s)", mock_status.get("http_status"))
    else:
        logger.warning("Mock Campaign API unreachable at startup: %s", mock_status.get("detail"))

    yield

    # Shutdown — close database connections and cleanup
    await MongoDB.disconnect()
    logger.info("MongoDB disconnected — application shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="CampaignX — AI Multi-Agent Marketing Automation Platform",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )

    # ── Routers ───────────────────────────────────────────────────
    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

    # ── Exception handlers ────────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "internal_server_error", "detail": str(exc)},
        )

    # ── Root endpoint ─────────────────────────────────────────────
    @app.get("/api", tags=["root"])
    async def root() -> dict:
        return {
            "message": "CampaignX API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
        }

    return app


app = create_app()
