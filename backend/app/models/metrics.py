"""Metrics data model for MongoDB metrics collection.

Aligned with Mock Campaign API — rates stored as decimals 0.0–1.0.
Percentage convenience properties multiply by 100 for display.
"""

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
    mock_campaign_id: str = Field(
        ..., description="Mock API campaign ID (required for API metrics)"
    )

    # Rates as decimals 0.0–1.0 matching Mock API response
    open_rate: float = Field(0.0, ge=0.0, le=1.0)
    click_rate: float = Field(0.0, ge=0.0, le=1.0)
    click_through_rate: float = Field(
        0.0, ge=0.0, le=1.0, description="CTR from Mock API"
    )

    # Counts
    total_sent: int = Field(0, ge=0)
    unique_opens: int = Field(0, ge=0)
    unique_clicks: int = Field(0, ge=0)

    performance_score: float = Field(
        0.0, description="Calculated: 0.7 * click_rate + 0.3 * open_rate"
    )

    # Timestamps
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    collected_at: Optional[datetime] = Field(
        None, description="When the data was collected from Mock API"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # --- Percentage convenience properties (read-only, not stored) ----------

    @property
    def open_rate_percentage(self) -> float:
        return round(self.open_rate * 100, 2)

    @property
    def click_rate_percentage(self) -> float:
        return round(self.click_rate * 100, 2)

    @property
    def ctr_percentage(self) -> float:
        return round(self.click_through_rate * 100, 2)

    # --- Validators ---------------------------------------------------------

    @model_validator(mode="after")
    def calculate_performance_score(self) -> "Metrics":
        """Auto-calculate performance_score from click_rate and open_rate."""
        self.performance_score = round(
            0.7 * self.click_rate + 0.3 * self.open_rate, 2
        )
        return self

    # --- Serialization ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model to a dictionary for MongoDB insertion."""
        return self.model_dump()

    @classmethod
    def from_mock_api(
        cls,
        data: dict[str, Any],
        variant_id: str,
        campaign_id: str,
        mock_campaign_id: str,
    ) -> "Metrics":
        """Create a Metrics instance from a Mock API /metrics response."""
        return cls(
            variant_id=variant_id,
            campaign_id=campaign_id,
            mock_campaign_id=mock_campaign_id,
            open_rate=float(data.get("open_rate", 0)),
            click_rate=float(data.get("click_rate", 0)),
            click_through_rate=float(data.get("click_through_rate", 0)),
            total_sent=int(data.get("total_sent", 0)),
            unique_opens=int(data.get("unique_opens", 0)),
            unique_clicks=int(data.get("unique_clicks", 0)),
            collected_at=datetime.utcnow(),
        )

    model_config = {"collection": "metrics"}


# Index definitions for the metrics collection
METRICS_INDEXES = [
    {"keys": [("metric_id", 1)], "unique": True},
    {"keys": [("variant_id", 1)]},
    {"keys": [("campaign_id", 1)]},
    {"keys": [("mock_campaign_id", 1)]},
    {"keys": [("performance_score", -1)]},
    {"keys": [("calculated_at", -1)]},
]
