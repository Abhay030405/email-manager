"""Campaign approval workflow endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.deps import CampaignRepoDep
from app.models.campaign import CampaignStatus
from app.schemas.approval import ApprovalRequest, ApprovalResponse

router = APIRouter(prefix="/approval", tags=["approval"])

_NOT_FOUND = "Campaign not found"
_404 = {404: {"description": _NOT_FOUND}}
_400 = {400: {"description": "Campaign is not in a state that can be approved/rejected"}}


@router.get("/pending", summary="List campaigns pending approval")
async def list_pending(repo: CampaignRepoDep) -> list[dict[str, Any]]:
    campaigns = await repo.find_pending_approval()
    return [c.model_dump() for c in campaigns]


@router.get("/{campaign_id}", responses=_404, summary="Get approval status")
async def get_approval_status(campaign_id: str, repo: CampaignRepoDep) -> dict[str, Any]:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return {
        "campaign_id": campaign_id,
        "status": campaign.status.value,
        "pending": campaign.status == CampaignStatus.PENDING_APPROVAL,
        "approved": campaign.status == CampaignStatus.APPROVED,
        "rejected": campaign.status == CampaignStatus.REJECTED,
    }


@router.post(
    "/{campaign_id}/approve",
    responses={**_404, **_400},
    summary="Approve a campaign",
)
async def approve_campaign(
    campaign_id: str,
    body: ApprovalRequest,
    repo: CampaignRepoDep,
) -> ApprovalResponse:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if campaign.status != CampaignStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Campaign is in status '{campaign.status.value}', not pending approval",
        )
    updated = await repo.update_status(campaign_id, CampaignStatus.APPROVED)
    if not updated:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return ApprovalResponse(
        campaign_id=campaign_id,
        status=CampaignStatus.APPROVED,
        approved_by=body.approved_by,
        notes=body.notes,
        message="Campaign approved successfully",
    )


@router.post(
    "/{campaign_id}/reject",
    responses={**_404, **_400},
    summary="Reject a campaign",
)
async def reject_campaign(
    campaign_id: str,
    body: ApprovalRequest,
    repo: CampaignRepoDep,
) -> ApprovalResponse:
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if campaign.status != CampaignStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Campaign is in status '{campaign.status.value}', not pending approval",
        )
    updated = await repo.update_status(campaign_id, CampaignStatus.REJECTED)
    if not updated:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return ApprovalResponse(
        campaign_id=campaign_id,
        status=CampaignStatus.REJECTED,
        approved_by=body.approved_by,
        notes=body.notes,
        message="Campaign rejected",
    )
