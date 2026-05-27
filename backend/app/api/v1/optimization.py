"""Optimization workflow endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.api.deps import CampaignRepoDep, DBDep, MetricsRepoDep
from app.db.repositories.optimization_repo import OptimizationRepository
from app.models.campaign import CampaignStatus
from app.schemas.common import WorkflowStatusResponse

router = APIRouter(prefix="/optimization", tags=["optimization"])

_NOT_FOUND = "Campaign not found"
_404 = {404: {"description": _NOT_FOUND}}
_400 = {400: {"description": "Bad request"}}
_500 = {500: {"description": "Internal server error"}}

_RUNNABLE = (CampaignStatus.APPROVED, CampaignStatus.EXECUTING, CampaignStatus.COMPLETED, CampaignStatus.OPTIMIZING)


@router.post(
    "/{campaign_id}/start",
    responses={**_404, **_400, **_500},
    summary="Start the optimization workflow for a campaign",
)
async def start_optimization(
    campaign_id: str,
    repo: CampaignRepoDep,
) -> WorkflowStatusResponse:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if campaign.status not in _RUNNABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot optimize campaign in status '{campaign.status.value}'",
        )
    try:
        from app.orchestration.optimization_graph import run_optimization_workflow
        result = await run_optimization_workflow(campaign_id)
        return WorkflowStatusResponse(
            campaign_id=campaign_id,
            status=result.get("status", "started"),
            message=result.get("message", "Optimization workflow triggered"),
            mock_api_campaign_ids=result.get("mock_api_campaign_ids") or {},
            error=result.get("error"),
            details=result,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/campaigns/{campaign_id}/optimize",
    responses={**_404, **_400},
    summary="Start full optimization workflow (background)",
)
async def start_full_optimization(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
    max_iterations: int = Query(3, ge=1, le=5),
    convergence_threshold: float = Query(0.05, ge=0.01, le=0.5),
    enable_ab_testing: bool = Query(True),
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if campaign.status not in _RUNNABLE:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot optimize campaign in status '{campaign.status.value}'",
        )

    from app.agents.optimization import OptimizationAgent
    from app.db.repositories.variant_iteration_repo import VariantIterationRepository
    from app.db.repositories.variant_repo import VariantRepository
    from app.db.repositories.ab_test_repo import ABTestRepository
    from app.services.performance_scoring_service import PerformanceScoringService
    from app.services.variant_regeneration_service import VariantRegenerationService
    from app.services.ab_testing_service import ABTestingService
    from app.services.optimization_service import OptimizationService

    variant_repo = VariantRepository(db)
    scoring_svc = PerformanceScoringService(metrics_repo, variant_repo)
    iteration_repo = VariantIterationRepository(db)
    regen_svc = VariantRegenerationService(scoring_svc, iteration_repo, variant_repo)
    ab_repo = ABTestRepository(db)
    ab_svc = ABTestingService(ab_repo, metrics_repo)
    opt_repo = OptimizationRepository(db)

    try:
        opt_agent = OptimizationAgent()
    except Exception:
        opt_agent = None  # type: ignore[assignment]

    svc = OptimizationService(
        optimization_agent=opt_agent,
        variant_regeneration_service=regen_svc,
        ab_testing_service=ab_svc,
        performance_scoring_service=scoring_svc,
        optimization_repo=opt_repo,
        metrics_repo=metrics_repo,
    )

    async def _run():
        await svc.execute_full_optimization_workflow(
            campaign_id, max_iterations, convergence_threshold, enable_ab_testing
        )

    background_tasks.add_task(_run)
    return {
        "campaign_id": campaign_id,
        "status": "started",
        "max_iterations": max_iterations,
        "convergence_threshold": convergence_threshold,
        "enable_ab_testing": enable_ab_testing,
        "message": "Optimization workflow started in background",
    }


@router.get(
    "/{campaign_id}/status",
    responses=_404,
    summary="Get optimization status for a campaign",
)
async def get_optimization_status(
    campaign_id: str,
    repo: CampaignRepoDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return {
        "campaign_id": campaign_id,
        "status": campaign.status.value,
        "optimizing": campaign.status == CampaignStatus.OPTIMIZING,
        "mock_campaign_id": campaign.mock_campaign_id,
    }


@router.get(
    "/campaigns/{campaign_id}/optimization-status",
    responses=_404,
    summary="Get detailed optimization status with iteration count",
)
async def get_detailed_optimization_status(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    opt_repo = OptimizationRepository(db)
    total = await opt_repo.count_iterations(campaign_id)
    latest = await opt_repo.get_latest_iteration(campaign_id)

    return {
        "campaign_id": campaign_id,
        "campaign_status": campaign.status.value,
        "total_iterations": total,
        "latest_iteration": latest.iteration_number if latest else None,
        "latest_score": latest.new_performance_score if latest else None,
        "converged": latest.convergence_achieved if latest else False,
        "status": latest.status if latest else "not_started",
    }


@router.get(
    "/campaigns/{campaign_id}/optimization-history",
    responses=_404,
    summary="Get optimization iteration history",
)
async def get_optimization_history(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    opt_repo = OptimizationRepository(db)
    results = await opt_repo.list_by_campaign(campaign_id, skip=skip, limit=limit)
    total = await opt_repo.count_iterations(campaign_id)

    return {
        "campaign_id": campaign_id,
        "total": total,
        "skip": skip,
        "limit": limit,
        "iterations": [r.model_dump() for r in results],
    }


@router.get(
    "/campaigns/{campaign_id}/optimization-insights",
    responses=_404,
    summary="Get optimization insights for current campaign state",
)
async def get_optimization_insights(
    campaign_id: str,
    repo: CampaignRepoDep,
    metrics_repo: MetricsRepoDep,
    db: DBDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    from app.db.repositories.variant_repo import VariantRepository
    from app.services.performance_scoring_service import PerformanceScoringService
    from app.utils.optimization_utils import generate_optimization_insights

    variant_repo = VariantRepository(db)
    scoring_svc = PerformanceScoringService(metrics_repo, variant_repo)
    poor_performers = await scoring_svc.identify_poor_performers(campaign_id)
    segment_perf = await scoring_svc.analyze_segment_performance(campaign_id)
    insights = generate_optimization_insights(poor_performers, segment_perf, [])

    return {
        "campaign_id": campaign_id,
        "poor_performers": poor_performers,
        "segment_performance": segment_perf,
        "insights": insights,
        "total_insights": len(insights),
    }


@router.get(
    "/{campaign_id}/results",
    responses=_404,
    summary="Get optimization results (metrics) for a campaign",
)
async def get_optimization_results(
    campaign_id: str,
    repo: CampaignRepoDep,
    metrics_repo: MetricsRepoDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    aggregates = await metrics_repo.calculate_campaign_aggregates(campaign_id)
    distribution = await metrics_repo.get_performance_distribution(campaign_id)
    top = await metrics_repo.get_top_performers(limit=3)

    return {
        "campaign_id": campaign_id,
        "status": campaign.status.value,
        "aggregates": aggregates,
        "variant_distribution": distribution,
        "top_performers": [m.model_dump() for m in top if m.campaign_id == campaign_id],
    }
