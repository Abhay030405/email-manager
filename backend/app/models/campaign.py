"""Campaign data model for MongoDB campaigns collection."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field, field_validator


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    OPTIMIZING = "optimizing"


class ProductDetails(BaseModel):
    product_name: str = ""
    product_description: str = ""
    cta_link: str = ""


class CampaignGoalData(BaseModel):
    objective: str = ""


class CampaignPreferences(BaseModel):
    email_tone: str = ""
    campaign_name: str = ""
    content_hints: str = ""


class ParsedData(BaseModel):
    """Structured data parsed from the campaign brief — matches parser agent output."""

    product_details: ProductDetails = Field(default_factory=ProductDetails)
    target_audience: dict[str, Any] = Field(default_factory=dict)
    campaign_goal: CampaignGoalData = Field(default_factory=CampaignGoalData)
    campaign_preferences: CampaignPreferences = Field(default_factory=CampaignPreferences)


class Campaign(BaseModel):
    """Campaign document model for MongoDB."""

    campaign_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Primary key, auto-generated UUID",
    )
    mock_campaign_id: Optional[str] = Field(
        None, description="Mock API campaign ID for tracking"
    )
    campaign_brief: str = Field(
        ..., min_length=1, description="Original natural language brief"
    )
    parsed_data: ParsedData = Field(default_factory=ParsedData)
    status: CampaignStatus = CampaignStatus.DRAFT
    segments: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    scheduled_time: Optional[datetime] = Field(
        None, description="Scheduled send time for Mock API integration"
    )

    @field_validator("campaign_brief")
    @classmethod
    def validate_brief(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("campaign_brief must not be empty")
        return v.strip()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a dictionary for MongoDB insertion."""
        return self.model_dump()

    model_config = {"collection": "campaigns"}


# Index definitions for the campaigns collection
CAMPAIGN_INDEXES = [
    {"keys": [("campaign_id", 1)], "unique": True},
    {"keys": [("mock_campaign_id", 1)]},
    {"keys": [("status", 1)]},
    {"keys": [("created_at", -1)]},
]
