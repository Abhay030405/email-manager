"""Alert management endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CampaignRepoDep, DBDep, MetricsRepoDep
from app.db.repositories.performance_alert_repo import PerformanceAlertRepository
from app.schemas.alerts import AcknowledgeRequest
from app.services.alert_service import AlertService
from app.utils.alert_rules_engine import AlertRulesEngine

router = APIRouter(prefix="/alerts", tags=["alerts"])

_NOT_FOUND = "Alert not found"
_404 = {404: {"description": _NOT_FOUND}}


def _alert_svc(db: DBDep, metrics_repo: MetricsRepoDep, campaign_repo: CampaignRepoDep) -> AlertService:
    from app.db.repositories.campaign_repo import CampaignRepository
    return AlertService(
        alert_repo=PerformanceAlertRepository(db),
        metrics_repo=metrics_repo,
        campaign_repo=campaign_repo,
        rules_engine=AlertRulesEngine(),
    )


@router.get("/active", summary="List active (unacknowledged) alerts")
async def get_active_alerts(
    db: DBDep,
    metrics_repo: MetricsRepoDep,
    repo: CampaignRepoDep,
    campaign_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
) -> list[dict[str, Any]]:
    svc = _alert_svc(db, metrics_repo, repo)
    alerts = await svc.get_active_alerts(campaign_id=campaign_id, severity=severity)
    return [a.model_dump() for a in alerts]


@router.get("/critical", summary="List all critical unacknowledged alerts")
async def get_critical_alerts(db: DBDep) -> list[dict[str, Any]]:
    repo = PerformanceAlertRepository(db)
    alerts = await repo.get_critical_alerts()
    return [a.model_dump() for a in alerts]


@router.get("/{alert_id}", responses=_404, summary="Get alert details")
async def get_alert(alert_id: str, db: DBDep) -> dict[str, Any]:
    repo = PerformanceAlertRepository(db)
    alert = await repo.find_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return alert.model_dump()


@router.post("/{alert_id}/acknowledge", responses=_404, summary="Acknowledge an alert")
async def acknowledge_alert(
    alert_id: str,
    body: AcknowledgeRequest,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
    repo: CampaignRepoDep,
) -> dict[str, Any]:
    svc = _alert_svc(db, metrics_repo, repo)
    alert = await svc.acknowledge_alert(alert_id, body.user, notes=body.notes)
    if not alert:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return alert.model_dump()


@router.get(
    "/campaign/{campaign_id}",
    summary="Get all alerts for a campaign",
)
async def get_campaign_alerts(
    campaign_id: str,
    db: DBDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
) -> list[dict[str, Any]]:
    repo = PerformanceAlertRepository(db)
    alerts = await repo.list_by_campaign(campaign_id, skip=skip, limit=limit)
    return [a.model_dump() for a in alerts]


@router.post(
    "/campaign/{campaign_id}/check",
    summary="Manually trigger alert check for a campaign",
)
async def check_campaign_alerts(
    campaign_id: str,
    db: DBDep,
    metrics_repo: MetricsRepoDep,
    repo: CampaignRepoDep,
) -> dict[str, Any]:
    svc = _alert_svc(db, metrics_repo, repo)
    alerts = await svc.check_and_trigger_alerts(campaign_id)
    return {
        "campaign_id": campaign_id,
        "alerts_triggered": len(alerts),
        "alerts": [a.model_dump() for a in alerts],
    }
