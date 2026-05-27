"""API v1 — aggregate router."""

from fastapi import APIRouter

from app.api.v1.ab_tests import router as ab_tests_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.approval import router as approval_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.customers import router as customers_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.execution import router as execution_router
from app.api.v1.health import router as health_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.optimization import router as optimization_router
from app.api.v1.segments import router as segments_router
from app.api.v1.variant_iterations import router as variant_iterations_router
from app.api.v1.websocket import router as websocket_router

v1_router = APIRouter()

v1_router.include_router(health_router)
v1_router.include_router(campaigns_router)
v1_router.include_router(customers_router)
v1_router.include_router(segments_router)
v1_router.include_router(metrics_router)
v1_router.include_router(approval_router)
v1_router.include_router(optimization_router)
v1_router.include_router(execution_router)
v1_router.include_router(analytics_router)
v1_router.include_router(alerts_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(websocket_router)
v1_router.include_router(ab_tests_router)
v1_router.include_router(variant_iterations_router)
