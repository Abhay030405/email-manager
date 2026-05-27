"""Health check endpoints."""

import time

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.db.mongodb import MongoDB
from app.schemas.common import HealthStatus, ServiceHealth

router = APIRouter(prefix="/health", tags=["health"])

_503 = {503: {"description": "Service unavailable"}}
_504 = {504: {"description": "Gateway timeout"}}


@router.get("", summary="Application health")
async def health() -> HealthStatus:
    settings = get_settings()
    return HealthStatus(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        services={},
    )


@router.get("/db", responses=_503, summary="Database connectivity")
async def health_db() -> ServiceHealth:
    start = time.monotonic()
    try:
        db = MongoDB.get_db()
        await db.client.admin.command("ping")
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        return ServiceHealth(status="ok", detail="MongoDB reachable", latency_ms=latency_ms)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@router.get("/mock-api", responses={**_503, **_504}, summary="Mock API connectivity")
async def health_mock_api() -> ServiceHealth:
    import httpx

    settings = get_settings()
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{settings.MOCK_CAMPAIGN_API_URL}/")
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        if resp.status_code < 500:
            return ServiceHealth(
                status="ok",
                detail=f"Mock API responded with {resp.status_code}",
                latency_ms=latency_ms,
            )
        raise HTTPException(status_code=503, detail=f"Mock API returned {resp.status_code}")
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Mock API timed out") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Mock API unreachable: {exc}") from exc


@router.get("/detailed", summary="Aggregate health check for all services")
async def detailed_health() -> HealthStatus:
    """Check MongoDB and Mock API together; return combined status."""
    settings = get_settings()
    services: dict[str, ServiceHealth] = {}

    # MongoDB
    t0 = time.monotonic()
    try:
        db = MongoDB.get_db()
        await db.client.admin.command("ping")
        services["mongodb"] = ServiceHealth(
            status="ok", latency_ms=round((time.monotonic() - t0) * 1000, 2)
        )
    except Exception as exc:
        services["mongodb"] = ServiceHealth(status="error", detail=str(exc)[:200])

    # Mock Campaign API (short timeout — informational, non-blocking)
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as hc:
            resp = await hc.get(f"{settings.MOCK_CAMPAIGN_API_URL}/")
        latency_ms = round((time.monotonic() - t0) * 1000, 2)
        svc_status = "ok" if resp.status_code < 500 else "degraded"
        services["mock_api"] = ServiceHealth(status=svc_status, latency_ms=latency_ms)
    except Exception as exc:
        services["mock_api"] = ServiceHealth(status="error", detail=str(exc)[:200])

    overall = "ok" if all(s.status == "ok" for s in services.values()) else "degraded"
    return HealthStatus(
        status=overall,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        services=services,
    )


@router.get("/ready", summary="Readiness probe — checks critical dependencies")
async def ready() -> dict:
    """Return 200 when the application is ready to serve traffic (DB connected)."""
    try:
        MongoDB.get_db()
        return {"status": "ready", "database": "connected"}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Not ready: {exc}") from exc
