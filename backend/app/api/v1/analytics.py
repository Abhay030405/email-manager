"""Analytics endpoints — trends, predictions, and segment analysis."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import CampaignRepoDep, DBDep, MetricsRepoDep
from app.db.repositories.analytics_repo import AnalyticsRepository
from app.db.repositories.metric_aggregation_repo import MetricAggregationRepository
from app.db.repositories.variant_repo import VariantRepository
from app.services.metrics_aggregation_service import MetricsAggregationService
from app.services.performance_analysis_service import PerformanceAnalysisService

router = APIRouter(prefix="/analytics", tags=["analytics"])

_NOT_FOUND = "Campaign not found"
_404 = {404: {"description": _NOT_FOUND}}


def _analysis_svc(db: DBDep, metrics_repo: MetricsRepoDep) -> PerformanceAnalysisService:
    return PerformanceAnalysisService(
        metrics_repo=metrics_repo,
        analytics_repo=AnalyticsRepository(db),
        aggregation_repo=MetricAggregationRepository(db),
        campaign_repo=None,  # type: ignore[arg-type]
    )


def _aggregation_svc(db: DBDep, metrics_repo: MetricsRepoDep) -> MetricsAggregationService:
    return MetricsAggregationService(
        metrics_repo=metrics_repo,
        aggregation_repo=MetricAggregationRepository(db),
        variant_repo=VariantRepository(db),
        campaign_repo=None,  # type: ignore[arg-type]
    )


@router.get(
    "/campaigns/{campaign_id}/analytics",
    responses=_404,
    summary="Comprehensive campaign analytics",
)
async def get_campaign_analytics(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    svc = _analysis_svc(db, metrics_repo)
    svc.campaign_repo = repo
    return await svc.analyze_campaign_performance(campaign_id)


@router.get(
    "/campaigns/{campaign_id}/trends",
    responses=_404,
    summary="Performance trend for a metric",
)
async def get_campaign_trends(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
    metric: str = Query("open_rate", description="Metric field name"),
    lookback_hours: int = Query(24, ge=1, le=720),
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    svc = _analysis_svc(db, metrics_repo)
    return await svc.calculate_trend(campaign_id, metric, lookback_hours)


@router.get(
    "/campaigns/{campaign_id}/segment-analysis",
    responses=_404,
    summary="Segment performance analysis",
)
async def get_segment_analysis(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
    segment_name: Optional[str] = Query(None),
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    svc = _analysis_svc(db, metrics_repo)
    if segment_name:
        return await svc.analyze_segment_performance(campaign_id, segment_name)
    return {"campaign_id": campaign_id, "segments": [], "message": "Provide segment_name query param"}


@router.get(
    "/campaigns/{campaign_id}/variant-comparison",
    responses=_404,
    summary="Compare variant performance",
)
async def get_variant_comparison(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    svc = _aggregation_svc(db, metrics_repo)
    return await svc.compare_variants(campaign_id)


@router.get(
    "/campaigns/{campaign_id}/time-to-metrics",
    responses=_404,
    summary="Time-to-event analysis",
)
async def get_time_to_metrics(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    svc = _analysis_svc(db, metrics_repo)
    return await svc.analyze_time_to_metrics(campaign_id)


@router.get(
    "/campaigns/{campaign_id}/predictions",
    responses=_404,
    summary="Predict final campaign metrics",
)
async def get_metric_predictions(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
    based_on_hours: int = Query(24, ge=1, le=168),
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    svc = _analysis_svc(db, metrics_repo)
    return await svc.predict_final_metrics(campaign_id, based_on_hours)


@router.get(
    "/campaigns/{campaign_id}/baseline-comparison",
    responses=_404,
    summary="Compare to historical campaign baselines",
)
async def get_baseline_comparison(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    svc = _analysis_svc(db, metrics_repo)
    svc.campaign_repo = repo
    return await svc.compare_to_baseline(campaign_id)
