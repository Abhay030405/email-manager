"""Campaign CRUD and workflow endpoints."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.deps import CampaignRepoDep, PageDep, SegmentRepoDep, VariantRepoDep
from app.models.campaign import Campaign, CampaignStatus
from app.models.schemas import CampaignCreate, CampaignUpdate
from app.schemas.common import PaginatedResponse, WorkflowStatusResponse

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

_NOT_FOUND = "Campaign not found"
_404 = {404: {"description": _NOT_FOUND}}
_400 = {400: {"description": "Bad request"}}
_500 = {500: {"description": "Internal server error"}}


@router.get("", summary="List campaigns")
async def list_campaigns(repo: CampaignRepoDep, page: PageDep) -> PaginatedResponse:
    items = await repo.list_all(skip=page.skip, limit=page.limit)
    total = await repo.count()
    return PaginatedResponse(
        items=[i.model_dump() for i in items],
        total=total,
        skip=page.skip,
        limit=page.limit,
        has_more=(page.skip + page.limit) < total,
    )


@router.post("", status_code=201, summary="Create a campaign")
async def create_campaign(body: CampaignCreate, repo: CampaignRepoDep) -> dict[str, Any]:
    campaign = Campaign(**body.model_dump())
    await repo.create(campaign)
    return campaign.model_dump()


@router.get("/{campaign_id}", responses=_404, summary="Get a campaign")
async def get_campaign(campaign_id: str, repo: CampaignRepoDep) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return campaign.model_dump()


@router.patch("/{campaign_id}", responses=_404, summary="Update a campaign")
async def update_campaign(
    campaign_id: str, body: CampaignUpdate, repo: CampaignRepoDep
) -> dict[str, Any]:
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)
    campaign = await repo.update(campaign_id, update_data)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return campaign.model_dump()


@router.delete(
    "/{campaign_id}",
    status_code=204,
    responses=_404,
    summary="Delete a campaign",
)
async def delete_campaign(campaign_id: str, repo: CampaignRepoDep) -> None:
    deleted = await repo.delete(campaign_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)


@router.post(
    "/{campaign_id}/run-workflow",
    responses={**_404, **_400, **_500},
    summary="Trigger the campaign creation workflow",
)
async def run_workflow(campaign_id: str, repo: CampaignRepoDep) -> WorkflowStatusResponse:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot run workflow for campaign in status '{campaign.status.value}'",
        )

    try:
        from app.orchestration.campaign_graph import run_campaign_workflow

        result = await run_campaign_workflow(campaign_id)
        return WorkflowStatusResponse(
            campaign_id=campaign_id,
            status=result.get("status", "started"),
            message=result.get("message", "Workflow triggered"),
            mock_api_campaign_ids=result.get("mock_api_campaign_ids"),
            error=result.get("error"),
            details=result,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/{campaign_id}/workflow-state",
    responses=_404,
    summary="Get the last known workflow state",
)
async def get_workflow_state(campaign_id: str, repo: CampaignRepoDep) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return {
        "campaign_id": campaign_id,
        "status": campaign.status.value,
        "mock_campaign_id": campaign.mock_campaign_id,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
    }


@router.get(
    "/{campaign_id}/pending-approval",
    responses=_404,
    summary="Check if campaign is pending approval",
)
async def pending_approval(campaign_id: str, repo: CampaignRepoDep) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return {
        "campaign_id": campaign_id,
        "pending": campaign.status == CampaignStatus.PENDING_APPROVAL,
        "status": campaign.status.value,
    }


@router.post(
    "/{campaign_id}/start",
    responses={**_404, **_400},
    summary="Start campaign workflow as background task",
)
async def start_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    repo: CampaignRepoDep,
) -> WorkflowStatusResponse:
    """Trigger the campaign creation workflow. Returns immediately; workflow runs in background."""
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start workflow for campaign in status '{campaign.status.value}'",
        )

    from app.orchestration.campaign_graph import run_campaign_workflow  # noqa: PLC0415

    background_tasks.add_task(run_campaign_workflow, campaign_id)
    return WorkflowStatusResponse(
        campaign_id=campaign_id,
        status="started",
        message="Campaign workflow started in background",
    )


@router.get(
    "/{campaign_id}/workflow-status",
    responses=_404,
    summary="Get workflow execution status",
)
async def get_workflow_status(campaign_id: str, repo: CampaignRepoDep) -> dict[str, Any]:
    """Return the latest persisted status for this campaign's workflow."""
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return {
        "campaign_id": campaign_id,
        "status": campaign.status.value,
        "mock_campaign_id": campaign.mock_campaign_id,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
    }


@router.get(
    "/{campaign_id}/segments",
    responses=_404,
    summary="Get customer segments for campaign",
)
async def get_campaign_segments(
    campaign_id: str,
    campaign_repo: CampaignRepoDep,
    segment_repo: SegmentRepoDep,
) -> dict[str, Any]:
    """Return all customer segments created for this campaign."""
    campaign = await campaign_repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    segments = await segment_repo.find_by_campaign(campaign_id)
    return {
        "campaign_id": campaign_id,
        "segments": [s.model_dump() for s in segments],
        "segment_count": len(segments),
    }


@router.get(
    "/{campaign_id}/variants",
    responses=_404,
    summary="Get all variants for campaign",
)
async def get_campaign_variants(
    campaign_id: str,
    campaign_repo: CampaignRepoDep,
    variant_repo: VariantRepoDep,
) -> dict[str, Any]:
    """Return all email variants generated for this campaign."""
    campaign = await campaign_repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    variants = await variant_repo.find_by_campaign(campaign_id)
    return {
        "campaign_id": campaign_id,
        "variants": [v.model_dump() for v in variants],
        "variant_count": len(variants),
    }
