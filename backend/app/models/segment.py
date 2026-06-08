"""Segment data model for MongoDB segments collection.

SegmentCriteria fields align with Mock Campaign API customer attributes.
"""

from datetime import datetime
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field, model_validator

_YN_DESC = "Y / N / None (any)"


def _age_range_to_filter(age_range: dict[str, int]) -> dict[str, int]:
    """Convert an age_range dict to min_age/max_age filter keys, swapping if inverted."""
    result: dict[str, int] = {}
    if age_range.get("min") is not None:
        result["min_age"] = age_range["min"]
    if age_range.get("max") is not None:
        result["max_age"] = age_range["max"]
    if result.get("min_age") and result.get("max_age") and result["min_age"] > result["max_age"]:
        result["min_age"], result["max_age"] = result["max_age"], result["min_age"]
    return result


class SegmentCriteria(BaseModel):
    """Demographic filter criteria stored with each segment document.

    These fields map 1-to-1 to the POST /api/customers/filter request body.
    """

    age_range: Optional[dict[str, int]] = Field(None, description="Age range with min/max keys")
    gender: Optional[str] = Field(None, description="Male / Female / Other")
    min_income: Optional[float] = Field(None, ge=0)
    max_income: Optional[float] = Field(None, ge=0)
    min_credit_score: Optional[int] = Field(None, ge=300, le=850)
    kyc_status: Optional[str] = Field(None, description=_YN_DESC)
    app_installed: Optional[str] = Field(None, description=_YN_DESC)
    social_media_active: Optional[str] = Field(None, description=_YN_DESC)
    existing_customer: Optional[str] = Field(None, description=_YN_DESC)

    def to_filter_body(self) -> dict[str, Any]:
        """Build the request body for POST /api/customers/filter."""
        body: dict[str, Any] = {}
        if self.age_range:
            body.update(_age_range_to_filter(self.age_range))
        if self.gender:
            body["gender"] = [self.gender]
        if self.min_income is not None:
            body["min_monthly_income"] = self.min_income
        if self.max_income is not None:
            body["max_monthly_income"] = self.max_income
        if self.min_credit_score is not None:
            body["min_credit_score"] = self.min_credit_score
        if self.kyc_status:
            body["kyc_status"] = self.kyc_status
        if self.app_installed:
            body["app_installed"] = self.app_installed
        if self.social_media_active:
            body["social_media_active"] = self.social_media_active
        if self.existing_customer:
            body["existing_customer"] = self.existing_customer
        return body


class Segment(BaseModel):
    """Segment document model for MongoDB."""

    segment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Primary key",
    )
    campaign_id: str = Field(..., description="Foreign key to campaigns")
    segment_name: str = ""
    description: str = Field("", description="AI-generated segment description")
    customer_ids: list[str] = Field(default_factory=list)
    segment_criteria: SegmentCriteria = Field(default_factory=SegmentCriteria)
    size: int = Field(0, ge=0, description="Number of customers in segment")
    targeting_priority: int = Field(1, ge=1, le=5, description="Segment priority from segmentation agent (1–5)")
    recommended_approach: str = Field("", description="Messaging approach from segmentation agent")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def sync_size_with_customer_ids(self) -> "Segment":
        """Keep size in sync with the actual customer_ids list length."""
        self.size = len(self.customer_ids)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a dictionary for MongoDB insertion."""
        return self.model_dump()

    model_config = {"collection": "segments"}


# Index definitions for the segments collection
SEGMENT_INDEXES = [
    {"keys": [("segment_id", 1)], "unique": True},
    {"keys": [("campaign_id", 1)]},
    {"keys": [("segment_name", 1)]},
]
