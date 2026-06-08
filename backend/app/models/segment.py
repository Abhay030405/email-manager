"""Segment data model for MongoDB segments collection.

SegmentCriteria fields align with Mock Campaign API customer attributes.
"""

from datetime import datetime
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field, model_validator

_YN_DESC = "Y / N / None (any)"


class SegmentCriteria(BaseModel):
    """Demographic filter criteria stored with each segment document."""

    age_range: Optional[dict[str, int]] = Field(None, description="Age range with min/max keys")
    gender: Optional[str] = Field(None, description="Male / Female / Other")
    min_income: Optional[float] = Field(None, ge=0)
    max_income: Optional[float] = Field(None, ge=0)
    min_credit_score: Optional[int] = Field(None, ge=300, le=850)
    kyc_status: Optional[str] = Field(None, description=_YN_DESC)
    app_installed: Optional[str] = Field(None, description=_YN_DESC)
    social_media_active: Optional[str] = Field(None, description=_YN_DESC)
    existing_customer: Optional[str] = Field(None, description=_YN_DESC)

    def matches_customer(self, customer: Any) -> bool:
        """Check whether a Customer instance satisfies all segment criteria."""
        return (
            self._check_age(customer)
            and self._check_financials(customer)
            and self._check_flags(customer)
        )

    def _check_age(self, customer: Any) -> bool:
        if self.age_range is not None:
            age_min = self.age_range.get("min", 0)
            age_max = self.age_range.get("max", 120)
            if not (age_min <= customer.Age <= age_max):
                return False
        if self.gender is not None and customer.Gender != self.gender:
            return False
        return True

    def _check_financials(self, customer: Any) -> bool:
        income = customer.Monthly_Income
        if self.min_income is not None and income < self.min_income:
            return False
        if self.max_income is not None and income > self.max_income:
            return False
        if self.min_credit_score is not None and customer.Credit_score < self.min_credit_score:
            return False
        return True

    def _check_flags(self, customer: Any) -> bool:
        checks = [
            (self.kyc_status,        customer.KYC_status),
            (self.app_installed,     customer.App_Installed),
            (self.social_media_active, customer.Social_Media_Active),
            (self.existing_customer, customer.Existing_Customer),
        ]
        return all(expected is None or customer_val == expected
                   for expected, customer_val in checks)


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
