"""Campaign request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.campaign import CampaignStatus, ParsedData

# Re-export existing CRUD schemas so route files can always import from app.schemas
from app.models.schemas import CampaignCreate, CampaignResponse, CampaignUpdate

__all__ = [
    # Existing CRUD schemas (thin re-exports)
    "CampaignCreate",
    "CampaignResponse",
    "CampaignUpdate",
    # Richer request schemas
    "CampaignCreateRequest",
    "CampaignUpdateRequest",
    # Richer response schemas
    "CampaignDetailResponse",
    "CampaignListResponse",
    "CampaignWorkflowStatus",
]


# ── Request schemas ───────────────────────────────────────────────────────────

class CampaignCreateRequest(BaseModel):
    """Stricter campaign creation body (min 50 chars ensures meaningful briefs)."""

    campaign_brief: str = Field(
        ...,
        min_length=50,
        max_length=5000,
        description="Natural language campaign brief — at least 50 characters",
    )
    created_by: str = Field("", description="Username or team identifier")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "campaign_brief": (
                        "Launch a summer sale campaign for running shoes targeting "
                        "active adults aged 20-40 in Mumbai and Delhi with a budget "
                        "of INR 5,00,000 and a CTA link to our product page."
                    ),
                    "created_by": "marketing_team",
                }
            ]
        }
    }


class CampaignUpdateRequest(BaseModel):
    """Partial update body — all fields optional."""

    campaign_brief: Optional[str] = Field(None, min_length=50, max_length=5000)
    status: Optional[str] = Field(
        None,
        description="One of: draft | pending_approval | approved | rejected | executing | completed | optimizing",
    )


# ── Response schemas ──────────────────────────────────────────────────────────

class CampaignDetailResponse(BaseModel):
    """Full campaign detail including strategy, variants, and Mock API mappings."""

    campaign_id: str
    campaign_brief: str
    parsed_data: ParsedData
    status: CampaignStatus
    segments: list[str]
    created_by: str
    mock_campaign_id: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None

    # Enriched fields (populated by the orchestration layer)
    strategy: dict[str, Any] = Field(
        default_factory=dict,
        description="AI-generated strategy from CampaignStrategyAgent",
    )
    variant_count: int = Field(0, ge=0, description="Number of variants generated")
    mock_api_campaign_ids: dict[str, str] = Field(
        default_factory=dict,
        description="variant_id -> Mock API campaign_id",
    )
    campaign_goals: list[str] = Field(
        default_factory=list,
        description="Parsed campaign goals from the brief",
    )

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    """Paginated campaign list response."""

    campaigns: list[CampaignResponse]
    total: int


# ── Workflow status ───────────────────────────────────────────────────────────

class CampaignWorkflowStatus(BaseModel):
    """Real-time state of a running campaign workflow."""

    campaign_id: str
    status: str = Field(..., description="running | completed | failed | pending")
    current_step: str = Field("", description="Name of the currently executing LangGraph node")
    progress_percentage: int = Field(0, ge=0, le=100, description="Estimated completion 0-100")
    error_messages: list[str] = Field(
        default_factory=list,
        description="Accumulated error messages from failed nodes",
    )
    mock_api_campaign_ids: dict[str, str] = Field(
        default_factory=dict,
        description="variant_id -> Mock API campaign_id (populated after scheduling)",
    )
