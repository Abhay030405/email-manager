"""Metrics data model for MongoDB metrics collection."""

from datetime import datetime
from typing import Any, Optional
import uuid

from pydantic import BaseModel, Field, model_validator


class Metrics(BaseModel):
    """Metrics document model for MongoDB."""

    metric_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Primary key",
    )
    variant_id: str = Field(..., description="Foreign key to campaign_variants")
    campaign_id: str = Field(..., description="Foreign key to campaigns")
    open_rate: float = Field(0.0, ge=0, le=100)
    click_rate: float = Field(0.0, ge=0, le=100)
    conversion_rate: Optional[float] = Field(None, ge=0, le=100)
    bounce_rate: Optional[float] = Field(None, ge=0, le=100)
    unsubscribe_rate: Optional[float] = Field(None, ge=0, le=100)
    emails_sent: int = Field(0, ge=0)
    emails_opened: int = Field(0, ge=0)
    emails_clicked: int = Field(0, ge=0)
    performance_score: float = Field(
        0.0, description="Calculated: 0.7 * click_rate + 0.3 * open_rate"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def calculate_performance_score(self) -> "Metrics":
        """Auto-calculate performance_score from click_rate and open_rate."""
        self.performance_score = round(
            0.7 * self.click_rate + 0.3 * self.open_rate, 2
        )
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a dictionary for MongoDB insertion."""
        return self.model_dump()

    model_config = {"collection": "metrics"}


# Index definitions for the metrics collection
METRICS_INDEXES = [
    {"keys": [("metric_id", 1)], "unique": True},
    {"keys": [("variant_id", 1)]},
    {"keys": [("campaign_id", 1)]},
    {"keys": [("performance_score", -1)]},
    {"keys": [("timestamp", -1)]},
]
