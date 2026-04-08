"""Campaign variant data model for MongoDB campaign_variants collection."""

from datetime import datetime
from enum import Enum
from typing import Any
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
    segment_name: str = ""
    subject_line: str = Field("", max_length=100)
    email_body: str = Field("", description="HTML or plain text email body")
    send_time: datetime = Field(default_factory=datetime.utcnow)
    variant_type: str = Field("", description="A/B test variant identifier")
    personalization_tags: list[str] = Field(default_factory=list)
    status: VariantStatus = VariantStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("subject_line")
    @classmethod
    def validate_subject_line(cls, v: str) -> str:
        if v and len(v) > 100:
            raise ValueError("Subject line must not exceed 100 characters")
        return v

    @field_validator("email_body")
    @classmethod
    def validate_email_body(cls, v: str) -> str:
        if v and len(v) < 50:
            raise ValueError(
                "Email body must be at least 50 characters when provided"
            )
        return v

    @field_validator("send_time")
    @classmethod
    def validate_send_time(cls, v: datetime) -> datetime:
        # Allow past times for already-sent variants loaded from DB
        return v

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a dictionary for MongoDB insertion."""
        return self.model_dump()

    model_config = {"collection": "campaign_variants"}


# Index definitions for the campaign_variants collection
VARIANT_INDEXES = [
    {"keys": [("variant_id", 1)], "unique": True},
    {"keys": [("campaign_id", 1)]},
    {"keys": [("segment_name", 1)]},
    {"keys": [("status", 1)]},
]
