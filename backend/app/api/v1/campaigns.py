"""Campaign CRUD and workflow endpoints."""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import CampaignRepoDep, MetricsRepoDep, MockClientDep, PageDep, SegmentRepoDep, VariantRepoDep
from app.models.campaign import Campaign, CampaignStatus
from app.models.schemas import CampaignCreate, CampaignUpdate
from app.schemas.common import PaginatedResponse, WorkflowStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


# ── Brief parsing schemas ─────────────────────────────────────────────────────

class ParseBriefRequest(BaseModel):
    brief_text: str = Field(..., min_length=1, description="Raw campaign brief text")


class ParsedBriefSections(BaseModel):
    product_details: dict[str, str]
    target_audience: dict[str, Any]   # {"Group 1": {…}, "Group 2": {…}, …}
    campaign_goal: dict[str, str]
    campaign_preferences: dict[str, str]


# ── Tone mapping helper ───────────────────────────────────────────────────────

_TONE_MAP: dict[str, str] = {
    "professional": "Formal",
    "formal": "Formal",
    "casual": "Friendly",
    "friendly": "Friendly",
    "urgent": "Urgent",
}


@router.post(
    "/parse-brief",
    responses={422: {"description": "Brief too vague to extract required fields"}, 500: {"description": "LLM parsing error"}},
    summary="Parse a campaign brief with LLM and return structured form data",
)
async def parse_campaign_brief(body: ParseBriefRequest) -> ParsedBriefSections:
    """Use the CampaignBriefParserAgent to extract structured form data from a brief."""
    try:
        from app.agents.brief_parser import CampaignBriefParserAgent

        agent = CampaignBriefParserAgent()
        result: dict[str, Any] = await agent.execute({"brief_text": body.brief_text})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM parsing failed: {exc}") from exc

    # Map preferred_tone enum → form label
    raw_tone = (result.get("preferred_tone") or "").lower()
    email_tone = _TONE_MAP.get(raw_tone, "")

    # Build content_hints from key_messages + constraints
    key_messages: list[str] = result.get("key_messages") or []
    constraints: str = result.get("constraints") or ""
    content_hints_parts = [", ".join(key_messages)] if key_messages else []
    if constraints:
        content_hints_parts.append(constraints)
    content_hints = ". ".join(content_hints_parts)

    # Map campaign_goal enum → human-readable fallback label
    _GOAL_LABELS: dict[str, str] = {
        "awareness": "Increase awareness",
        "conversion": "Drive sign-ups / conversions",
        "retention": "Retain existing customers",
        "engagement": "Maximize engagement",
    }
    raw_goal = (result.get("campaign_goal") or "").lower()
    fallback_label = _GOAL_LABELS.get(raw_goal, result.get("campaign_goal") or "")
    # Prefer the full descriptive objective extracted from the brief
    objective = result.get("campaign_objective") or fallback_label

    ta = result.get("target_audience") or {}
    groups: dict = ta if isinstance(ta, dict) else {}

    return ParsedBriefSections(
        product_details={
            "product_name": result.get("product_name") or "",
            "product_description": result.get("product_description") or "",
            "cta_link": result.get("cta_link") or "",
        },
        target_audience=groups,
        campaign_goal={
            "objective": objective,
        },
        campaign_preferences={
            "email_tone": email_tone,
            "campaign_name": result.get("campaign_name") or "",
            "content_hints": content_hints,
        },
    )

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
    campaign = Campaign(**body.model_dump(exclude_none=True))
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

        result = await run_campaign_workflow(campaign_id, campaign.campaign_brief)
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

    background_tasks.add_task(run_campaign_workflow, campaign_id, campaign.campaign_brief)
    return WorkflowStatusResponse(
        campaign_id=campaign_id,
        status="started",
        message="Campaign workflow started in background",
    )


@router.post(
    "/{campaign_id}/execute",
    responses={**_404, **_400, **_500},
    summary="Execute an approved campaign — schedule variants via Mock API",
)
async def execute_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    repo: CampaignRepoDep,
) -> WorkflowStatusResponse:
    """Run execution_node directly from saved workflow state. Call after approving a campaign."""
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if campaign.status not in {CampaignStatus.APPROVED, CampaignStatus.PENDING_APPROVAL}:
        raise HTTPException(
            status_code=400,
            detail=f"Campaign must be approved before executing (current status: '{campaign.status.value}')",
        )

    async def _run(cid: str) -> None:
        try:
            from app.orchestration.campaign_graph import execution_node  # noqa: PLC0415
            from app.orchestration.state import StateManager  # noqa: PLC0415

            sm = StateManager()
            try:
                state = await sm.load_state(cid)
            except ValueError:
                logger.warning("No workflow state for campaign %s — cannot execute without variants", cid)
                return
            state["approval_status"] = "approved"
            result_state = await execution_node(state)
            await sm.save_state(result_state, cid)
        except Exception as exc:
            logger.error("Background execution failed for campaign %s: %s", cid, exc)

    background_tasks.add_task(_run, campaign_id)
    return WorkflowStatusResponse(
        campaign_id=campaign_id,
        status="executing",
        message="Execution started — variants are being scheduled via Mock API",
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
    "/{campaign_id}/metrics",
    responses={**_404, **_500},
    summary="Fetch latest metrics from Mock API for all campaign variants",
)
async def get_campaign_live_metrics(
    campaign_id: str,
    repo: CampaignRepoDep,
    metrics_repo: MetricsRepoDep,
    client: MockClientDep,
) -> list[dict[str, Any]]:
    """Pull fresh metrics from Mock API for every variant, upsert to MongoDB, and return all."""
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)

    try:
        from app.orchestration.state import StateManager  # noqa: PLC0415
        from app.models.metrics import Metrics  # noqa: PLC0415

        state_manager = StateManager()
        state = await state_manager.load_state(campaign_id)
        mock_ids: dict[str, str] = dict(state.get("mock_api_campaign_ids") or {})
    except ValueError:
        mock_ids = {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load workflow state: {exc}") from exc

    for variant_id, mock_campaign_id in mock_ids.items():
        try:
            data = client.get_campaign_metrics(mock_campaign_id)
            metrics = Metrics(
                variant_id=variant_id,
                campaign_id=campaign_id,
                mock_campaign_id=mock_campaign_id,
                open_rate=float(data.get("open_rate", 0)),
                click_rate=float(data.get("click_rate", 0)),
                click_through_rate=float(data.get("click_through_rate", 0)),
                total_sent=int(data.get("total_sent", 0)),
                unique_opens=int(data.get("unique_opens", 0)),
                unique_clicks=int(data.get("unique_clicks", 0)),
            )
            await metrics_repo.upsert(metrics)
        except Exception:
            pass  # skip failed variants; return whatever we have

    items = await metrics_repo.find_by_campaign(campaign_id)
    return [i.model_dump() for i in items]


@router.get(
    "/{campaign_id}/strategy",
    responses={**_404, **_500},
    summary="Get AI-generated strategy for campaign",
)
async def get_campaign_strategy(campaign_id: str, repo: CampaignRepoDep) -> dict[str, Any]:
    """Return the AI-generated strategy from the campaign workflow state."""
    campaign = await repo.find_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    try:
        from app.orchestration.state import StateManager  # noqa: PLC0415

        state_manager = StateManager()
        state = await state_manager.load_state(campaign_id)
        strategy: dict[str, Any] = dict(state.get("strategy") or {})
    except ValueError:
        strategy = {}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load strategy: {exc}") from exc
    return {"campaign_id": campaign_id, "strategy": strategy if strategy else None}


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
