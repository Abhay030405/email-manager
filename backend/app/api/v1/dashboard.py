"""Dashboard summary endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CampaignRepoDep, DBDep, MetricsRepoDep
from app.db.repositories.performance_alert_repo import PerformanceAlertRepository
from app.models.campaign import CampaignStatus
from app.services.performance_analysis_service import PerformanceAnalysisService
from app.db.repositories.analytics_repo import AnalyticsRepository
from app.db.repositories.customer_repo import CustomerRepository
from app.db.repositories.metric_aggregation_repo import MetricAggregationRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_NOT_FOUND = "Campaign not found"
_404 = {404: {"description": _NOT_FOUND}}


@router.get("/overview", summary="Get dashboard overview metrics")
async def get_dashboard_overview(
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
) -> dict[str, Any]:
    alert_repo = PerformanceAlertRepository(db)

    active_campaigns = await repo.find_all(filter={"status": CampaignStatus.EXECUTING.value})
    completed_campaigns = await repo.find_all(filter={"status": CampaignStatus.COMPLETED.value})
    active_alerts = await alert_repo.list_active_alerts()
    critical_alerts = await alert_repo.get_critical_alerts()

    # Average metrics across all completed campaigns
    all_metrics = []
    for c in completed_campaigns[:10]:
        agg = await metrics_repo.calculate_campaign_aggregates(c.campaign_id)
        all_metrics.append(agg)

    avg_open = 0.0
    avg_click = 0.0
    if all_metrics:
        avg_open = sum(m.get("avg_open_rate", 0.0) for m in all_metrics) / len(all_metrics) * 100
        avg_click = sum(m.get("avg_click_rate", 0.0) for m in all_metrics) / len(all_metrics) * 100

    recent = await repo.find_all(skip=0, limit=5)

    return {
        "active_campaigns": len(active_campaigns),
        "completed_campaigns": len(completed_campaigns),
        "active_alerts": len(active_alerts),
        "critical_alerts": len(critical_alerts),
        "avg_open_rate": round(avg_open, 2),
        "avg_click_rate": round(avg_click, 2),
        "recent_campaigns": [
            {"campaign_id": c.campaign_id, "status": c.status.value, "brief": c.campaign_brief[:80]}
            for c in recent
        ],
    }


@router.get(
    "/campaign/{campaign_id}",
    responses=_404,
    summary="Get dashboard data for a single campaign",
)
async def get_campaign_dashboard(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    svc = PerformanceAnalysisService(
        metrics_repo=metrics_repo,
        analytics_repo=AnalyticsRepository(db),
        aggregation_repo=MetricAggregationRepository(db),
        customer_repo=CustomerRepository(db),
        campaign_repo=repo,
    )
    alert_repo = PerformanceAlertRepository(db)

    analysis = await svc.analyze_campaign_performance(campaign_id)
    alerts = await alert_repo.list_active_alerts(campaign_id=campaign_id)

    return {
        "campaign_id": campaign_id,
        "status": campaign.status.value,
        "current_metrics": analysis.get("overall_metrics", {}),
        "trends": analysis.get("trends", {}),
        "active_alerts": [a.model_dump() for a in alerts],
        "recommendations": analysis.get("recommendations", []),
    }
