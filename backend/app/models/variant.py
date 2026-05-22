"""Campaign variant data model for MongoDB campaign_variants collection.

Aligned with Mock Campaign API requirements for scheduling and tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field, field_validator


class VariantStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELLED = "cancelled"


class CampaignVariant(BaseModel):
    """Campaign variant document model for MongoDB."""

    variant_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Primary key",
    )
    campaign_id: str = Field(..., description="Foreign key to campaigns")
    mock_campaign_id: Optional[str] = Field(
        None, description="Mock API campaign ID if sent via API"
    )
    segment_name: str = ""
    subject_line: str = Field("", max_length=200)
    email_body: str = Field(
        "", max_length=5000, description="HTML or plain text email body"
    )
    send_time: datetime = Field(default_factory=datetime.utcnow)
    variant_type: str = Field("", description="A/B test variant identifier e.g. var_1")
    personalization_tags: list[str] = Field(default_factory=list)
    status: VariantStatus = VariantStatus.DRAFT
    customer_ids: list[str] = Field(
        default_factory=list, description="Customer IDs targeted in this variant"
    )
    campaign_metadata: Optional[dict[str, Any]] = Field(
        None, description="Arbitrary metadata for Mock API"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("subject_line")
    @classmethod
    def validate_subject_line(cls, v: str) -> str:
        if v and len(v) > 200:
            raise ValueError("Subject line must not exceed 200 characters")
        return v

    @field_validator("email_body")
    @classmethod
    def validate_email_body(cls, v: str) -> str:
        if v and len(v) > 5000:
            raise ValueError("Email body must not exceed 5000 characters")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a dictionary for MongoDB insertion."""
        return self.model_dump()

    def to_mock_api_payload(self) -> dict[str, Any]:
        """Format variant data for Mock API /api/campaigns/schedule endpoint."""
        return {
            "subject_line": self.subject_line,
            "email_body": self.email_body,
            "customer_ids": self.customer_ids,
            "send_time": self.send_time.isoformat(),
            "campaign_metadata": self.campaign_metadata or {},
        }

    model_config = {"collection": "campaign_variants"}


# Index definitions for the campaign_variants collection
VARIANT_INDEXES = [
    {"keys": [("variant_id", 1)], "unique": True},
    {"keys": [("campaign_id", 1)]},
    {"keys": [("mock_campaign_id", 1)]},
    {"keys": [("segment_name", 1)]},
    {"keys": [("status", 1)]},
]
