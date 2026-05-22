"""Pydantic schemas for Mock Campaign API request and response payloads.

These models validate data at the boundary between our application and the
external Mock Campaign API at https://mock-campaign-api.onrender.com.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Customer responses ─────────────────────────────────────────────────────


class CustomerRecord(BaseModel):
    """Single customer record from GET /api/customers."""

    customer_id: str
    Full_name: str = ""
    email: str = ""
    Age: int = 0
    Gender: str = ""
    Marital_Status: str = ""
    Family_Size: int = 0
    Dependent_count: int = Field(0, alias="Dependent count")
    Occupation: str = ""
    Occupation_type: str = Field("", alias="Occupation type")
    Monthly_Income: int = 0
    KYC_status: str = Field("", alias="KYC status")
    City: str = ""
    Kids_in_Household: int = 0
    App_Installed: str = ""
    Existing_Customer: str = Field("", alias="Existing Customer")
    Credit_score: int = 0
    Social_Media_Active: str = ""

    model_config = {"populate_by_name": True}


class CustomerCountResponse(BaseModel):
    """Response from GET /api/customers/count."""

    count: int = Field(0, alias="count")
    total: int = Field(0, alias="total")

    def get_count(self) -> int:
        return self.count or self.total


class CustomerValidationRequest(BaseModel):
    """Request body for POST /api/customers/validate."""

    customer_ids: list[str] = Field(..., min_length=1)


class CustomerValidationResponse(BaseModel):
    """Response from POST /api/customers/validate."""

    valid_ids: list[str] = Field(default_factory=list)
    invalid_ids: list[str] = Field(default_factory=list)
    total_valid: int = 0


# ── Campaign schedule ──────────────────────────────────────────────────────


class CampaignScheduleRequest(BaseModel):
    """Request body for POST /api/campaigns/schedule."""

    customer_ids: list[str] = Field(..., min_length=1)
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    scheduled_time: str
    segment_name: str = ""
    variant_id: str = ""
    campaign_metadata: Optional[dict[str, Any]] = None

    @field_validator("scheduled_time", mode="before")
    @classmethod
    def coerce_datetime(cls, v: Any) -> str:
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


class CampaignScheduleResponse(BaseModel):
    """Response from POST /api/campaigns/schedule."""

    campaign_id: str
    status: str = "scheduled"
    total_customers: int = 0
    scheduled_time: str = ""


# ── Campaign metrics ───────────────────────────────────────────────────────


class CampaignMetricsResponse(BaseModel):
    """Response from GET /api/campaigns/{campaign_id}/metrics.

    All rates are returned as decimals 0.0–1.0 by the Mock API.
    """

    campaign_id: str = ""
    total_sent: int = 0
    unique_opens: int = 0
    unique_clicks: int = 0
    open_rate: float = Field(0.0, ge=0.0, le=1.0)
    click_rate: float = Field(0.0, ge=0.0, le=1.0)
    click_through_rate: float = Field(0.0, ge=0.0, le=1.0)

    @property
    def performance_score(self) -> float:
        return round(0.7 * self.click_rate + 0.3 * self.open_rate, 4)


# ── Campaign results ───────────────────────────────────────────────────────


class CustomerResultRecord(BaseModel):
    """Single record from GET /api/campaigns/{campaign_id}/results."""

    campaign_id: str = ""
    customer_id: str
    opened: bool = False
    clicked: bool = False
    open_probability: float = Field(0.0, ge=0.0, le=1.0)
    click_probability: float = Field(0.0, ge=0.0, le=1.0)


# ── API error ──────────────────────────────────────────────────────────────


class APIErrorResponse(BaseModel):
    """Generic error body returned by the Mock Campaign API."""

    detail: str = ""
    message: str = ""
    error: str = ""

    def get_message(self) -> str:
        return self.detail or self.message or self.error or "Unknown API error"
