"""Segment data model for MongoDB segments collection.

SegmentCriteria fields align with Mock Campaign API customer attributes.
"""

from datetime import datetime
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field, model_validator


class SegmentCriteria(BaseModel):
    """Demographic filter criteria matching Mock API customer fields."""

    age_range: dict[str, int] = Field(
        default_factory=lambda: {"min": 0, "max": 120},
        description="Age range with min/max keys",
    )
    gender: list[str] = Field(
        default_factory=list, description="Male / Female / Other"
    )
    cities: list[str] = Field(
        default_factory=list, description="Indian cities filter"
    )
    marital_status: list[str] = Field(
        default_factory=list,
        description="Married / Single / Divorced / Widowed",
    )
    occupation_type: list[str] = Field(
        default_factory=list,
        description="Full-time / Part-time / Self-employed / Retired / Student",
    )
    min_income: Optional[float] = Field(None, ge=0)
    max_income: Optional[float] = Field(None, ge=0)
    credit_score_range: dict[str, int] = Field(
        default_factory=lambda: {"min": 300, "max": 850},
        description="Credit score range",
    )
    app_installed: Optional[str] = Field(
        None, description="Y / N / None (any)"
    )
    social_media_active: Optional[str] = Field(
        None, description="Y / N / None (any)"
    )
    existing_customer: Optional[str] = Field(
        None, description="Y / N / None (any)"
    )

    def matches_customer(self, customer: Any) -> bool:
        """Check whether a Customer instance satisfies all segment criteria."""
        age_min = self.age_range.get("min", 0)
        age_max = self.age_range.get("max", 120)
        if not (age_min <= customer.Age <= age_max):
            return False

        if self.gender and customer.Gender not in self.gender:
            return False

        if self.cities and customer.City not in self.cities:
            return False

        if self.marital_status and customer.Marital_Status not in self.marital_status:
            return False

        if self.occupation_type and customer.Occupation_type not in self.occupation_type:
            return False

        if self.min_income is not None and customer.Monthly_Income < self.min_income:
            return False
        if self.max_income is not None and customer.Monthly_Income > self.max_income:
            return False

        cs_min = self.credit_score_range.get("min", 300)
        cs_max = self.credit_score_range.get("max", 850)
        if not (cs_min <= customer.Credit_score <= cs_max):
            return False

        if self.app_installed is not None and customer.App_Installed != self.app_installed:
            return False
        if self.social_media_active is not None and customer.Social_Media_Active != self.social_media_active:
            return False
        if self.existing_customer is not None and customer.Existing_Customer != self.existing_customer:
            return False

        return True


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
