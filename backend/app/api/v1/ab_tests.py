"""A/B test management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DBDep, MetricsRepoDep
from app.db.repositories.ab_test_repo import ABTestRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.services.ab_testing_service import ABTestingService

router = APIRouter(prefix="/ab-tests", tags=["ab-tests"])

_NOT_FOUND = "A/B test not found"
_404 = {404: {"description": _NOT_FOUND}}


def _svc(db: DBDep, metrics_repo: MetricsRepoDep) -> ABTestingService:
    return ABTestingService(
        ab_test_repo=ABTestRepository(db),
        metrics_repo=metrics_repo,
    )


@router.post(
    "/campaigns/{campaign_id}/ab-tests",
    responses=_404,
    summary="Create and start an A/B test for two variants",
)
async def create_ab_test(
    campaign_id: str,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
    variant_a_id: str = Query(...),
    variant_b_id: str = Query(...),
    test_duration_hours: int = Query(24, ge=1, le=168),
) -> dict[str, Any]:
    svc = _svc(db, metrics_repo)
    test = await svc.setup_ab_test(campaign_id, variant_a_id, variant_b_id, test_duration_hours)
    return test.model_dump()


@router.get(
    "/campaigns/{campaign_id}/ab-tests",
    summary="List A/B tests for a campaign",
)
async def list_ab_tests(
    campaign_id: str,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    repo = ABTestRepository(db)
    tests = await repo.list_by_campaign(campaign_id, skip=skip, limit=limit)
    return {
        "campaign_id": campaign_id,
        "total": len(tests),
        "tests": [t.model_dump() for t in tests],
    }


@router.get(
    "/{test_id}",
    responses=_404,
    summary="Get A/B test details",
)
async def get_ab_test(test_id: str, db: DBDep, metrics_repo: MetricsRepoDep) -> dict[str, Any]:
    repo = ABTestRepository(db)
    test = await repo.find_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return test.model_dump()


@router.post(
    "/{test_id}/analyze",
    responses=_404,
    summary="Analyze a completed A/B test",
)
async def analyze_ab_test(
    test_id: str, db: DBDep, metrics_repo: MetricsRepoDep
) -> dict[str, Any]:
    svc = _svc(db, metrics_repo)
    try:
        test = await svc.run_ab_test(test_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return test.model_dump()


@router.get(
    "/{test_id}/recommendation",
    responses=_404,
    summary="Get recommendation from A/B test results",
)
async def get_ab_test_recommendation(
    test_id: str, db: DBDep, metrics_repo: MetricsRepoDep
) -> dict[str, Any]:
    repo = ABTestRepository(db)
    test = await repo.find_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    svc = _svc(db, metrics_repo)
    rec = await svc.recommend_winning_variant(test)
    return {"test_id": test_id, **rec}
