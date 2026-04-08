"""Segment data model for MongoDB segments collection."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, Field, model_validator


class SegmentCriteria(BaseModel):
    """Demographic filter criteria for a segment."""

    age_range: list[int] = Field(default_factory=lambda: [0, 150])
    gender: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    activity_status: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


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
