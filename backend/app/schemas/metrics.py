"""Metrics request / response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# Re-export existing CRUD schemas
from app.models.schemas import MetricsCreate, MetricsResponse, MetricsUpdate

__all__ = [
    # Existing CRUD schemas (thin re-exports)
    "MetricsCreate",
    "MetricsResponse",
    "MetricsUpdate",
    # Richer / display-oriented schemas
    "CampaignMetricsResponse",
    "CustomerResultSchema",
]


# ── Display-oriented metrics (percentage format) ──────────────────────────────

class CampaignMetricsResponse(BaseModel):
    """Metrics response with rates expressed as percentages (0–100) for display.

    The DB model stores rates as decimals 0.0–1.0; this schema multiplies by 100
    so the frontend never needs to do that conversion itself.
    """

    campaign_id: str
    mock_api_campaign_id: str
    total_sent: int = Field(..., ge=0)
    unique_opens: int = Field(..., ge=0)
    unique_clicks: int = Field(..., ge=0)

    # Percentage form (0–100) — multiply DB decimal by 100 before serialising
    open_rate: float = Field(..., ge=0, le=100, description="Open rate as percentage 0–100")
    click_rate: float = Field(..., ge=0, le=100, description="Click rate as percentage 0–100")
    click_through_rate: float = Field(..., ge=0, le=100, description="CTR as percentage 0–100")

    # Performance score stays 0.0–1.0 (composite, not a percentage)
    performance_score: float = Field(..., ge=0, le=1)

    collected_at: Optional[datetime] = None

    @classmethod
    def from_metrics(cls, m: "MetricsResponse") -> "CampaignMetricsResponse":
        """Convert a decimal-rate MetricsResponse to the percentage display form."""
        return cls(
            campaign_id=m.campaign_id,
            mock_api_campaign_id=m.mock_campaign_id,
            total_sent=m.total_sent,
            unique_opens=m.unique_opens,
            unique_clicks=m.unique_clicks,
            open_rate=round(m.open_rate * 100, 2),
            click_rate=round(m.click_rate * 100, 2),
            click_through_rate=round(m.click_through_rate * 100, 2),
            performance_score=m.performance_score,
            collected_at=m.collected_at,
        )


# ── Per-customer result schema ────────────────────────────────────────────────

class CustomerResultSchema(BaseModel):
    """Predicted engagement result for a single customer (Mock API response)."""

    customer_id: str
    opened: bool
    clicked: bool
    open_probability: float = Field(..., ge=0, le=1)
    click_probability: float = Field(..., ge=0, le=1)
