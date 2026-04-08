"""Pydantic request/response schemas for the API layer."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.campaign import CampaignStatus, ParsedData
from app.models.customer import ActivityStatus, Gender, Preferences, PurchaseRecord
from app.models.metrics import Metrics
from app.models.segment import SegmentCriteria
from app.models.variant import VariantStatus


# ── Customer Schemas ──────────────────────────────────────────────

class CustomerCreate(BaseModel):
    customer_id: str
    age: int = Field(..., ge=0, le=120)
    gender: Gender
    location: str
    activity_status: ActivityStatus = ActivityStatus.ACTIVE
    purchase_history: list[PurchaseRecord] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "customer_id": "CUST-0001",
                    "age": 28,
                    "gender": "male",
                    "location": "New York",
                    "activity_status": "active",
                    "purchase_history": [
                        {"product": "Sneakers", "amount": 120.00, "date": "2026-01-15T10:00:00"}
                    ],
                    "preferences": {"tags": ["fitness", "sports"], "categories": ["premium"]},
                }
            ]
        }
    }


class CustomerUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=0, le=120)
    gender: Optional[Gender] = None
    location: Optional[str] = None
    activity_status: Optional[ActivityStatus] = None
    purchase_history: Optional[list[PurchaseRecord]] = None
    preferences: Optional[Preferences] = None


class CustomerResponse(BaseModel):
    customer_id: str
    age: int
    gender: Gender
    location: str
    activity_status: ActivityStatus
    purchase_history: list[PurchaseRecord]
    preferences: Preferences
    created_at: datetime
    updated_at: datetime


# ── Campaign Schemas ──────────────────────────────────────────────

class CampaignCreate(BaseModel):
    campaign_brief: str = Field(..., min_length=1)
    created_by: str = ""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "campaign_brief": "Launch summer sale for running shoes targeting active users aged 20-40 with $5000 budget",
                    "created_by": "marketing_team",
                }
            ]
        }
    }


class CampaignUpdate(BaseModel):
    campaign_brief: Optional[str] = None
    parsed_data: Optional[ParsedData] = None
    status: Optional[CampaignStatus] = None
    segments: Optional[list[str]] = None


class CampaignResponse(BaseModel):
    campaign_id: str
    campaign_brief: str
    parsed_data: ParsedData
    status: CampaignStatus
    segments: list[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None


# ── Variant Schemas ───────────────────────────────────────────────

class VariantCreate(BaseModel):
    campaign_id: str
    segment_name: str = ""
    subject_line: str = Field("", max_length=100)
    email_body: str = ""
    send_time: Optional[datetime] = None
    variant_type: str = ""
    personalization_tags: list[str] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "campaign_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "segment_name": "young_active_males",
                    "subject_line": "Crush Your Next Run – 30% Off",
                    "email_body": "<h1>Run Faster</h1><p>Our new Running Shoes Pro X are built for performance. Shop now!</p>",
                    "variant_type": "A",
                    "personalization_tags": ["first_name", "location"],
                }
            ]
        }
    }


class VariantUpdate(BaseModel):
    subject_line: Optional[str] = Field(None, max_length=100)
    email_body: Optional[str] = None
    send_time: Optional[datetime] = None
    status: Optional[VariantStatus] = None
    personalization_tags: Optional[list[str]] = None


class VariantResponse(BaseModel):
    variant_id: str
    campaign_id: str
    segment_name: str
    subject_line: str
    email_body: str
    send_time: datetime
    variant_type: str
    personalization_tags: list[str]
    status: VariantStatus
    created_at: datetime


# ── Metrics Schemas ───────────────────────────────────────────────

class MetricsCreate(BaseModel):
    variant_id: str
    campaign_id: str
    open_rate: float = Field(0.0, ge=0, le=100)
    click_rate: float = Field(0.0, ge=0, le=100)
    conversion_rate: Optional[float] = Field(None, ge=0, le=100)
    bounce_rate: Optional[float] = Field(None, ge=0, le=100)
    unsubscribe_rate: Optional[float] = Field(None, ge=0, le=100)
    emails_sent: int = Field(0, ge=0)
    emails_opened: int = Field(0, ge=0)
    emails_clicked: int = Field(0, ge=0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "variant_id": "v-001",
                    "campaign_id": "c-001",
                    "open_rate": 35.5,
                    "click_rate": 12.3,
                    "emails_sent": 2000,
                    "emails_opened": 710,
                    "emails_clicked": 246,
                }
            ]
        }
    }


class MetricsUpdate(BaseModel):
    open_rate: Optional[float] = Field(None, ge=0, le=100)
    click_rate: Optional[float] = Field(None, ge=0, le=100)
    conversion_rate: Optional[float] = Field(None, ge=0, le=100)
    bounce_rate: Optional[float] = Field(None, ge=0, le=100)
    unsubscribe_rate: Optional[float] = Field(None, ge=0, le=100)
    emails_sent: Optional[int] = Field(None, ge=0)
    emails_opened: Optional[int] = Field(None, ge=0)
    emails_clicked: Optional[int] = Field(None, ge=0)


class MetricsResponse(BaseModel):
    metric_id: str
    variant_id: str
    campaign_id: str
    open_rate: float
    click_rate: float
    conversion_rate: Optional[float]
    bounce_rate: Optional[float]
    unsubscribe_rate: Optional[float]
    emails_sent: int
    emails_opened: int
    emails_clicked: int
    performance_score: float
    timestamp: datetime
    last_updated: datetime


# ── Segment Schemas ───────────────────────────────────────────────

class SegmentCreate(BaseModel):
    campaign_id: str
    segment_name: str
    description: str = ""
    customer_ids: list[str] = Field(default_factory=list)
    segment_criteria: SegmentCriteria = Field(default_factory=SegmentCriteria)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "campaign_id": "c-001",
                    "segment_name": "young_active_males",
                    "description": "Male customers aged 20-35 with active status",
                    "customer_ids": ["CUST-0001", "CUST-0005"],
                    "segment_criteria": {
                        "age_range": [20, 35],
                        "gender": ["male"],
                        "activity_status": ["active"],
                    },
                }
            ]
        }
    }


class SegmentUpdate(BaseModel):
    segment_name: Optional[str] = None
    description: Optional[str] = None
    customer_ids: Optional[list[str]] = None
    segment_criteria: Optional[SegmentCriteria] = None


class SegmentResponse(BaseModel):
    segment_id: str
    campaign_id: str
    segment_name: str
    description: str
    customer_ids: list[str]
    segment_criteria: SegmentCriteria
    size: int
    created_at: datetime
