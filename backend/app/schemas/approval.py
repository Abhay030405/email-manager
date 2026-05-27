"""Approval workflow request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.campaign import CampaignStatus

__all__ = [
    "ApprovalRequest",
    "ApprovalResponse",
    "ApprovalActionRequest",
    "ApprovalResultResponse",
]


# ── Original schemas (used by existing route files) ───────────────────────────

class ApprovalRequest(BaseModel):
    """Body for POST /campaigns/{id}/approve or /reject."""

    approved_by: str = Field("", description="Username or user_id of the approver")
    notes: str = Field("", description="Optional review notes")


class ApprovalResponse(BaseModel):
    """Returned after a campaign approve / reject action."""

    campaign_id: str
    status: CampaignStatus
    approved_by: str = ""
    notes: str = ""
    approved_at: Optional[datetime] = None
    message: str = ""


# ── Richer schemas (spec Task 5.5) ────────────────────────────────────────────

class ApprovalActionRequest(BaseModel):
    """Single-body schema that encodes both approve and reject actions."""

    campaign_id: str = Field(..., description="Campaign to approve or reject")
    action: str = Field(
        ...,
        pattern=r"^(approve|reject)$",
        description="Must be 'approve' or 'reject'",
    )
    feedback: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional reviewer feedback / rejection reason",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"campaign_id": "camp-001", "action": "approve", "feedback": "Looks great!"},
                {"campaign_id": "camp-002", "action": "reject", "feedback": "Brief too vague."},
            ]
        }
    }


class ApprovalResultResponse(BaseModel):
    """Returned after processing an ApprovalActionRequest."""

    campaign_id: str
    status: str = Field(..., description="approved | rejected")
    approved_at: datetime
    approved_variants: list[str] = Field(
        default_factory=list,
        description="variant_ids that were approved and scheduled",
    )
    feedback: Optional[str] = None
