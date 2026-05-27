"""Campaign execution endpoints — trigger execution and query logs."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CampaignRepoDep, DBDep, PageDep
from app.db.repositories.execution_log_repo import ExecutionLogRepository
from app.models.campaign import CampaignStatus

router = APIRouter(prefix="/execution", tags=["execution"])

_NOT_FOUND = "Campaign not found"
_404 = {404: {"description": _NOT_FOUND}}
_400 = {400: {"description": "Bad request"}}
_500 = {500: {"description": "Internal server error"}}


@router.post(
    "/{campaign_id}/execute",
    responses={**_404, **_400, **_500},
    summary="Trigger campaign execution via the Mock Campaign API",
)
async def execute_campaign(
    campaign_id: str,
    repo: CampaignRepoDep,
) -> dict[str, Any]:
    """Run the execution agent for an approved campaign.

    The campaign must be in APPROVED or EXECUTING status.  The workflow
    updates the campaign status to EXECUTING during the run.
    """
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    runnable = {CampaignStatus.APPROVED, CampaignStatus.EXECUTING}
    if campaign.status not in runnable:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute campaign in status '{campaign.status.value}'",
        )

    try:
        from app.orchestration.optimization_graph import run_optimization_workflow

        result = await run_optimization_workflow(campaign_id)
        return {
            "campaign_id": campaign_id,
            "status": result.get("status", "started"),
            "message": result.get("message", "Execution triggered"),
            "mock_api_campaign_ids": result.get("mock_api_campaign_ids") or {},
            "error": result.get("error"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/{campaign_id}/execution-logs",
    responses=_404,
    summary="List execution log entries for a campaign",
)
async def get_execution_logs(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
    page: PageDep,
) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    log_repo = ExecutionLogRepository(db)
    logs = await log_repo.find_by_campaign(campaign_id)
    status_counts = await log_repo.count_by_status(campaign_id)

    # Apply pagination manually (logs are already newest-first)
    paginated = logs[page.skip: page.skip + page.limit]

    return {
        "campaign_id": campaign_id,
        "logs": [log.model_dump() for log in paginated],
        "total": len(logs),
        "status_counts": status_counts,
        "skip": page.skip,
        "limit": page.limit,
    }


@router.post(
    "/{campaign_id}/retry-execution",
    responses={**_404, **_400, **_500},
    summary="Retry failed execution attempts for a campaign",
)
async def retry_execution(
    campaign_id: str,
    repo: CampaignRepoDep,
    db: DBDep,
) -> dict[str, Any]:
    """Re-trigger the execution workflow for variants that previously failed.

    Only campaigns in APPROVED or EXECUTING status may be retried.
    """
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    retryable = {CampaignStatus.APPROVED, CampaignStatus.EXECUTING}
    if campaign.status not in retryable:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry execution for campaign in status '{campaign.status.value}'",
        )

    log_repo = ExecutionLogRepository(db)
    failed_logs = await log_repo.find_failed(campaign_id)

    if not failed_logs:
        return {
            "campaign_id": campaign_id,
            "message": "No failed executions found — nothing to retry",
            "retried_variants": [],
        }

    failed_variant_ids = [log.variant_id for log in failed_logs]

    try:
        from app.orchestration.optimization_graph import run_optimization_workflow

        result = await run_optimization_workflow(campaign_id)
        return {
            "campaign_id": campaign_id,
            "message": "Retry execution triggered",
            "retried_variants": failed_variant_ids,
            "status": result.get("status", "started"),
            "mock_api_campaign_ids": result.get("mock_api_campaign_ids") or {},
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
