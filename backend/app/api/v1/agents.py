"""Individual agent test endpoints — callable one-by-one from Swagger UI.

Each endpoint runs exactly one agent in isolation using context loaded from
MongoDB (campaign document, segment collection, workflow state).  They are
intentionally side-effect-free: they do NOT persist the agent output back to
the DB so re-running them is always safe.

Typical test sequence:
  1. POST /agents/parse-brief          (no campaign needed)
  2. POST /campaigns                   (create campaign with confirmed data)
  3. POST /agents/segmentation         { campaign_id }
  4. POST /agents/strategy             { campaign_id }  (needs segments in DB)
  5. POST /agents/content-generation   { campaign_id }  (needs strategy in state)
  6. POST /agents/approval             { campaign_id }
  7. POST /agents/monitoring           { campaign_id }  (needs mock_api_campaign_ids)
  8. POST /agents/optimization         { campaign_id }  (needs metrics in state)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import CampaignRepoDep, MockClientDep, SegmentRepoDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agent Tests"])

_404 = {404: {"description": "Campaign not found"}}
_422 = {422: {"description": "Prerequisite not met — run the previous agent step first"}}
_500 = {500: {"description": "Agent error"}}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _require_campaign(campaign: Any, campaign_id: str) -> None:
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign '{campaign_id}' not found")


async def _load_workflow_state(campaign_id: str) -> dict[str, Any]:
    from app.orchestration.state import StateManager
    try:
        sm = StateManager()
        return await sm.load_state(campaign_id)
    except ValueError:
        return {}


# ── Request bodies ────────────────────────────────────────────────────────────

class ParseBriefRequest(BaseModel):
    brief_text: str = Field(..., min_length=1, description="Raw campaign brief text")


class CampaignIdRequest(BaseModel):
    campaign_id: str = Field(..., description="ID of an existing campaign in MongoDB")


class ContentGenRequest(BaseModel):
    campaign_id: str = Field(..., description="ID of an existing campaign in MongoDB")
    segment_name: str | None = Field(
        None,
        description="Name of the segment to generate content for. Defaults to the first available segment.",
    )


# ── 1. Parse Brief ────────────────────────────────────────────────────────────

@router.post(
    "/parse-brief",
    responses={422: {"description": "Brief too vague"}, **_500},
    summary="[Agent 1] CampaignBriefParserAgent — parse a raw brief",
)
async def test_parse_brief(body: ParseBriefRequest) -> dict[str, Any]:
    """Run CampaignBriefParserAgent on any raw brief text and return the
    nested ParsedBriefSections (product_details, target_audience, campaign_goal,
    campaign_preferences).  No campaign needs to exist."""
    try:
        from app.agents.brief_parser import CampaignBriefParserAgent
        agent = CampaignBriefParserAgent()
        result = await agent.execute({"brief_text": body.brief_text})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
    return result


# ── 2. Segmentation ───────────────────────────────────────────────────────────

@router.post(
    "/segmentation",
    responses={**_404, **_422, **_500},
    summary="[Agent 2] CustomerSegmentationAgent — segment customers for a campaign",
)
async def test_segmentation(
    body: CampaignIdRequest,
    campaign_repo: CampaignRepoDep,
) -> dict[str, Any]:
    """Load target_audience from the campaign's parsed_data and run
    CustomerSegmentationAgent, which calls POST /api/customers/filter on the
    Mock API — no local customer data needed.  Segments are NOT saved to the DB."""
    campaign = await campaign_repo.find_by_id(body.campaign_id)
    _require_campaign(campaign, body.campaign_id)

    parsed_data = campaign.parsed_data.model_dump() if campaign.parsed_data else {}
    target_audience_raw = parsed_data.get("target_audience", {})
    campaign_goal_raw = parsed_data.get("campaign_goal", {})
    campaign_goal_str = campaign_goal_raw.get("objective", "") if isinstance(campaign_goal_raw, dict) else str(campaign_goal_raw)

    try:
        from app.agents.segmentation import CustomerSegmentationAgent
        agent = CustomerSegmentationAgent()
        result = await agent.execute({
            "target_audience": target_audience_raw,
            "campaign_goal": campaign_goal_str,
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Segmentation agent error: {exc}") from exc

    return result


# ── 3. Strategy ───────────────────────────────────────────────────────────────

@router.post(
    "/strategy",
    responses={**_404, **_422, **_500},
    summary="[Agent 3] CampaignStrategyAgent — generate strategy for a campaign",
)
async def test_strategy(
    body: CampaignIdRequest,
    campaign_repo: CampaignRepoDep,
    segment_repo: SegmentRepoDep,
) -> dict[str, Any]:
    """Load parsed_data from the campaign and segment details from MongoDB,
    then run CampaignStrategyAgent.  Run Agent 2 first to populate segments."""
    campaign = await campaign_repo.find_by_id(body.campaign_id)
    _require_campaign(campaign, body.campaign_id)

    segments = await segment_repo.find_by_campaign(body.campaign_id)
    if not segments:
        raise HTTPException(
            status_code=422,
            detail="No segments found for this campaign. Run /agents/segmentation first.",
        )

    parsed_brief = campaign.parsed_data.model_dump() if campaign.parsed_data else {}

    segment_entries = [
        {
            "segment_name": s.segment_name,
            "description": s.description,
            "customer_ids": s.customer_ids,
            "size": len(s.customer_ids),
            "targeting_priority": s.targeting_priority,
            "recommended_approach": s.recommended_approach,
        }
        for s in segments
    ]

    try:
        from app.agents.strategy import CampaignStrategyAgent
        agent = CampaignStrategyAgent()
        result = await agent.execute({
            "parsed_brief": parsed_brief,
            "segments": segment_entries,
            "current_time": datetime.now(tz=timezone.utc),
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Strategy agent error: {exc}") from exc

    return result


# ── 4. Content Generation ─────────────────────────────────────────────────────

@router.post(
    "/content-generation",
    responses={**_404, **_422, **_500},
    summary="[Agent 4] ContentGenerationAgent — generate email variant for one segment",
)
async def test_content_generation(
    body: ContentGenRequest,
    campaign_repo: CampaignRepoDep,
    segment_repo: SegmentRepoDep,
) -> dict[str, Any]:
    """Load parsed_data + strategy from workflow state, pick the requested
    segment (defaults to first), and run ContentGenerationAgent.
    Run Agents 2 & 3 first to populate segments and strategy."""
    campaign = await campaign_repo.find_by_id(body.campaign_id)
    _require_campaign(campaign, body.campaign_id)

    segments = await segment_repo.find_by_campaign(body.campaign_id)
    if not segments:
        raise HTTPException(
            status_code=422,
            detail="No segments found. Run /agents/segmentation first.",
        )

    # Pick segment
    if body.segment_name:
        seg = next((s for s in segments if s.segment_name == body.segment_name), None)
        if not seg:
            names = [s.segment_name for s in segments]
            raise HTTPException(
                status_code=404,
                detail=f"Segment '{body.segment_name}' not found. Available: {names}",
            )
    else:
        seg = segments[0]

    # Load strategy from workflow state (may be empty if strategy hasn't run yet)
    state = await _load_workflow_state(body.campaign_id)
    strategy = state.get("strategy") or {}

    parsed_brief = campaign.parsed_data.model_dump() if campaign.parsed_data else {}

    campaign_prefix = body.campaign_id.split("-")[0]
    variant_id = f"{campaign_prefix}_v_test"

    segment_payload = {
        "segment_name": seg.segment_name,
        "description": seg.description,
        "customer_ids": seg.customer_ids,
        "size": len(seg.customer_ids),
        "targeting_priority": seg.targeting_priority,
        "recommended_approach": seg.recommended_approach,
    }

    try:
        from app.agents.content_gen import ContentGenerationAgent
        agent = ContentGenerationAgent()
        result = await agent.execute({
            "parsed_brief": parsed_brief,
            "segment": segment_payload,
            "variant_id": variant_id,
            "strategy": strategy,
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Content generation agent error: {exc}") from exc

    return result


# ── 5. Approval ───────────────────────────────────────────────────────────────

@router.post(
    "/approval",
    responses={**_404, **_500},
    summary="[Agent 5] ApprovalAgent — check campaign approval status",
)
async def test_approval(
    body: CampaignIdRequest,
    campaign_repo: CampaignRepoDep,
) -> dict[str, Any]:
    """Run ApprovalAgent — reads campaign status from MongoDB and returns
    'approved' | 'rejected' | 'pending'."""
    campaign = await campaign_repo.find_by_id(body.campaign_id)
    _require_campaign(campaign, body.campaign_id)

    try:
        from app.agents.approval import ApprovalAgent
        agent = ApprovalAgent()
        result = await agent.execute({"campaign_id": body.campaign_id})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Approval agent error: {exc}") from exc

    return result


# ── 6. Monitoring ─────────────────────────────────────────────────────────────

@router.post(
    "/monitoring",
    responses={**_404, **_422, **_500},
    summary="[Agent 6] MonitoringAgent — fetch live metrics from Mock API",
)
async def test_monitoring(
    body: CampaignIdRequest,
    campaign_repo: CampaignRepoDep,
) -> dict[str, Any]:
    """Load mock_api_campaign_ids from workflow state, then run MonitoringAgent
    to pull fresh metrics from Mock API.  Requires execution to have run."""
    campaign = await campaign_repo.find_by_id(body.campaign_id)
    _require_campaign(campaign, body.campaign_id)

    state = await _load_workflow_state(body.campaign_id)
    mock_api_campaign_ids: dict[str, str] = dict(state.get("mock_api_campaign_ids") or {})

    if not mock_api_campaign_ids:
        raise HTTPException(
            status_code=422,
            detail="No Mock API campaign IDs found. Campaign must be executed first.",
        )

    try:
        from app.agents.monitoring import MonitoringAgent
        agent = MonitoringAgent()
        result = await agent.execute({
            "campaign_id": body.campaign_id,
            "mock_api_campaign_ids": mock_api_campaign_ids,
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Monitoring agent error: {exc}") from exc

    return result


# ── 7. Optimization ───────────────────────────────────────────────────────────

@router.post(
    "/optimization",
    responses={**_404, **_422, **_500},
    summary="[Agent 7] OptimizationAgent — generate improvement recommendations",
)
async def test_optimization(
    body: CampaignIdRequest,
    campaign_repo: CampaignRepoDep,
) -> dict[str, Any]:
    """Load collected metrics from workflow state, then run OptimizationAgent
    to produce per-variant improvement recommendations.  Requires monitoring
    to have run at least once."""
    campaign = await campaign_repo.find_by_id(body.campaign_id)
    _require_campaign(campaign, body.campaign_id)

    state = await _load_workflow_state(body.campaign_id)
    metrics = state.get("metrics") or {}

    if not metrics:
        raise HTTPException(
            status_code=422,
            detail="No metrics found in workflow state. Run /agents/monitoring first.",
        )

    try:
        from app.agents.optimization import OptimizationAgent
        agent = OptimizationAgent()
        result = await agent.execute({
            "campaign_id": body.campaign_id,
            "metrics": metrics,
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Optimization agent error: {exc}") from exc

    return result
