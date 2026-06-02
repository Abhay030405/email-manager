"""Pydantic request/response schemas for the API layer.

Updated for Mock Campaign API integration — customer fields match the
18-field Indian-demographic schema; metrics use 0.0–1.0 decimal rates.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.models.campaign import CampaignStatus, ParsedData
from app.models.metrics import Metrics
from app.models.segment import SegmentCriteria
from app.models.variant import VariantStatus


# ── Customer Schemas ──────────────────────────────────────────────

class CustomerCreate(BaseModel):
    customer_id: str = Field(..., pattern=r"^CUST\d{4}$")
    Full_name: str = Field(..., min_length=1)
    email: str
    Age: int = Field(..., ge=0, le=120)
    Gender: Literal["Male", "Female", "Other"]
    Marital_Status: Literal["Married", "Single", "Divorced", "Widowed"] = "Single"
    Family_Size: int = Field(1, ge=1, le=10)
    Dependent_count: int = Field(0, ge=0, alias="Dependent count")
    Occupation: str = ""
    Occupation_type: Literal[
        "Full-time", "Part-time", "Self-employed", "Retired", "Student"
    ] = Field("Full-time", alias="Occupation type")
    Monthly_Income: float = Field(0, ge=0)
    KYC_status: Literal["Y", "N"] = Field("N", alias="KYC status")
    City: str = ""
    Kids_in_Household: int = Field(0, ge=0)
    App_Installed: Literal["Y", "N"] = "N"
    Existing_Customer: Literal["Y", "N"] = Field("N", alias="Existing Customer")
    Credit_score: int = Field(300, ge=300, le=850)
    Social_Media_Active: Literal["Y", "N"] = "N"

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "customer_id": "CUST0001",
                    "Full_name": "Ravi Sharma",
                    "email": "ravi.sharma@example.com",
                    "Age": 32,
                    "Gender": "Male",
                    "Marital_Status": "Married",
                    "City": "Mumbai",
                    "Monthly_Income": 75000.0,
                    "Credit_score": 720,
                    "App_Installed": "Y",
                    "Social_Media_Active": "Y",
                }
            ]
        },
    }


class CustomerUpdate(BaseModel):
    Full_name: Optional[str] = None
    email: Optional[str] = None
    Age: Optional[int] = Field(None, ge=0, le=120)
    Gender: Optional[Literal["Male", "Female", "Other"]] = None
    Marital_Status: Optional[Literal["Married", "Single", "Divorced", "Widowed"]] = None
    Family_Size: Optional[int] = Field(None, ge=1, le=10)
    Dependent_count: Optional[int] = Field(None, ge=0)
    Occupation: Optional[str] = None
    Occupation_type: Optional[
        Literal["Full-time", "Part-time", "Self-employed", "Retired", "Student"]
    ] = None
    Monthly_Income: Optional[float] = Field(None, ge=0)
    KYC_status: Optional[Literal["Y", "N"]] = None
    City: Optional[str] = None
    Kids_in_Household: Optional[int] = Field(None, ge=0)
    App_Installed: Optional[Literal["Y", "N"]] = None
    Existing_Customer: Optional[Literal["Y", "N"]] = None
    Credit_score: Optional[int] = Field(None, ge=300, le=850)
    Social_Media_Active: Optional[Literal["Y", "N"]] = None


class CustomerResponse(BaseModel):
    customer_id: str
    Full_name: str
    email: str
    Age: int
    Gender: str
    Marital_Status: str
    Family_Size: int
    Dependent_count: int
    Occupation: str
    Occupation_type: str
    Monthly_Income: float
    KYC_status: str
    City: str
    Kids_in_Household: int
    App_Installed: str
    Existing_Customer: str
    Credit_score: int
    Social_Media_Active: str
    synced_from_mock_api: bool
    created_at: datetime
    updated_at: datetime


# ── Campaign Schemas ──────────────────────────────────────────────

class CampaignCreate(BaseModel):
    campaign_brief: str = Field(..., min_length=1)
    parsed_data: Optional[ParsedData] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "campaign_brief": "Launch summer sale for running shoes targeting active users aged 20-40",
                    "parsed_data": {
                        "product_details": {"product_name": "Running Shoes", "product_description": "Premium running shoes", "cta_link": "https://example.com/shop"},
                        "target_audience": {"Group 1": {"min_age": 20, "max_age": 40}},
                        "campaign_goal": {"objective": "Drive sign-ups / conversions"},
                        "campaign_preferences": {"email_tone": "Friendly", "campaign_name": "Summer Sale 2026", "content_hints": ""},
                    },
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
    mock_campaign_id: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None


# ── Variant Schemas ───────────────────────────────────────────────

class VariantCreate(BaseModel):
    campaign_id: str
    segment_name: str = ""
    subject_line: str = Field("", max_length=200)
    email_body: str = Field("", max_length=5000)
    send_time: Optional[datetime] = None
    variant_type: str = ""
    personalization_tags: list[str] = Field(default_factory=list)
    customer_ids: list[str] = Field(default_factory=list)
    campaign_metadata: Optional[dict[str, Any]] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "campaign_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "segment_name": "young_urban_males",
                    "subject_line": "Ravi, exclusive offer just for you!",
                    "email_body": "<h1>Special Deal</h1><p>Get 30% off premium plans.</p>",
                    "variant_type": "var_1",
                    "customer_ids": ["CUST0001", "CUST0002"],
                    "personalization_tags": ["Full_name", "City"],
                }
            ]
        }
    }


class VariantUpdate(BaseModel):
    subject_line: Optional[str] = Field(None, max_length=200)
    email_body: Optional[str] = Field(None, max_length=5000)
    send_time: Optional[datetime] = None
    status: Optional[VariantStatus] = None
    personalization_tags: Optional[list[str]] = None
    customer_ids: Optional[list[str]] = None
    mock_campaign_id: Optional[str] = None


class VariantResponse(BaseModel):
    variant_id: str
    campaign_id: str
    mock_campaign_id: Optional[str] = None
    segment_name: str
    subject_line: str
    email_body: str
    send_time: datetime
    variant_type: str
    personalization_tags: list[str]
    customer_ids: list[str]
    status: VariantStatus
    created_at: datetime


# ── Metrics Schemas ───────────────────────────────────────────────

class MetricsCreate(BaseModel):
    variant_id: str
    campaign_id: str
    mock_campaign_id: str
    open_rate: float = Field(0.0, ge=0.0, le=1.0)
    click_rate: float = Field(0.0, ge=0.0, le=1.0)
    click_through_rate: float = Field(0.0, ge=0.0, le=1.0)
    total_sent: int = Field(0, ge=0)
    unique_opens: int = Field(0, ge=0)
    unique_clicks: int = Field(0, ge=0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "variant_id": "v-001",
                    "campaign_id": "c-001",
                    "mock_campaign_id": "mc-001",
                    "open_rate": 0.355,
                    "click_rate": 0.123,
                    "total_sent": 2000,
                    "unique_opens": 710,
                    "unique_clicks": 246,
                }
            ]
        }
    }


class MetricsUpdate(BaseModel):
    open_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    click_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    click_through_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    total_sent: Optional[int] = Field(None, ge=0)
    unique_opens: Optional[int] = Field(None, ge=0)
    unique_clicks: Optional[int] = Field(None, ge=0)


class MetricsResponse(BaseModel):
    metric_id: str
    variant_id: str
    campaign_id: str
    mock_campaign_id: str
    open_rate: float
    click_rate: float
    click_through_rate: float
    total_sent: int
    unique_opens: int
    unique_clicks: int
    performance_score: float
    calculated_at: datetime
    collected_at: Optional[datetime] = None
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
                    "segment_name": "young_urban_males",
                    "description": "Male customers aged 20-35 in metro cities",
                    "customer_ids": ["CUST0001", "CUST0005"],
                    "segment_criteria": {
                        "age_range": {"min": 20, "max": 35},
                        "gender": ["Male"],
                        "cities": ["Mumbai", "Delhi"],
                        "app_installed": "Y",
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


# ── Agent I/O Schemas ─────────────────────────────────────────────
# These mirror the internal agent schemas but live here for API / cross-module
# use and JSON schema generation.

# Brief Parser ────────────────────────────────────────────────────

class BriefInputSchema(BaseModel):
    """API-level input for the CampaignBriefParserAgent."""

    brief_text: str = Field(..., min_length=1, description="Natural language campaign brief")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "brief_text": (
                        "Launch summer sale for running shoes targeting active users "
                        "aged 20-40 with $5000 budget. CTA: https://example.com/sale"
                    )
                }
            ]
        }
    }


class ParsedBriefSchema(BaseModel):
    """Structured output of the CampaignBriefParserAgent."""

    product_name: str = Field(..., description="Name of the product or service")
    product_description: str = Field("Not specified", description="Short product description")
    target_audience: str = Field(..., description="Who the campaign targets")
    campaign_goal: str = Field(
        ..., description="One of: awareness | conversion | retention | engagement"
    )
    cta_link: str = Field("", description="Call-to-action URL")
    budget: Optional[float] = Field(None, description="Campaign budget in USD")
    preferred_tone: str = Field(
        "professional", description="One of: professional | casual | friendly | urgent"
    )
    key_messages: list[str] = Field(default_factory=list, description="3-5 key selling points")
    constraints: Optional[str] = Field(None, description="Restrictions or compliance notes")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "product_name": "CloudStorage Pro",
                    "product_description": "Cloud storage plan for SMBs",
                    "target_audience": "SMB owners aged 30-50",
                    "campaign_goal": "conversion",
                    "cta_link": "https://example.com/pro",
                    "budget": 8000.0,
                    "preferred_tone": "professional",
                    "key_messages": ["500 GB storage", "Team collaboration", "99.9% uptime"],
                    "constraints": None,
                }
            ]
        }
    }


# Segmentation ────────────────────────────────────────────────────

class SegmentationInputSchema(BaseModel):
    """API-level input for the CustomerSegmentationAgent."""

    customers: list[CustomerResponse] = Field(..., description="Customer list to segment")
    target_audience: str = Field(..., min_length=1, description="Target audience from parsed brief")
    campaign_goal: str = Field(..., description="One of: awareness | conversion | retention | engagement")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "customers": [],
                    "target_audience": "Active users aged 20-40",
                    "campaign_goal": "conversion",
                }
            ]
        }
    }


class SegmentOutSchema(BaseModel):
    """A single named customer segment (agent output)."""

    segment_name: str = Field(..., description="Snake_case descriptive name")
    description: str = Field(..., description="Why this segment matters")
    customer_ids: list[str] = Field(default_factory=list)
    size: int = Field(0, ge=0)
    targeting_priority: int = Field(..., ge=1, le=5, description="1=lowest, 5=highest")
    recommended_approach: str = Field(..., description="Short tactical guidance")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "segment_name": "millennials_active",
                    "description": "Active millennial customers aged 25-34",
                    "customer_ids": ["CUST0001", "CUST0002"],
                    "size": 2,
                    "targeting_priority": 4,
                    "recommended_approach": "Use benefit-led copy with mobile-first design.",
                }
            ]
        }
    }


class SegmentationResultSchema(BaseModel):
    """Full output of the CustomerSegmentationAgent."""

    segments: list[SegmentOutSchema]
    total_customers: int
    coverage_pct: float = Field(..., description="Percentage of customers assigned to ≥1 segment")
    distribution: dict[str, int] = Field(default_factory=dict, description="segment_name → count")


# Strategy ────────────────────────────────────────────────────────

class ABTestPlanSchema(BaseModel):
    """A/B test configuration."""

    num_variants: int = Field(..., ge=2, le=4, description="Number of test variants (2–4)")
    variant_distribution: dict[str, float] = Field(
        ..., description="variant_id → percentage share (must sum to 100)"
    )
    test_dimension: str = Field(
        ..., description="What is being tested: subject_line | content | send_time | cta | tone"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "num_variants": 2,
                    "variant_distribution": {"variant_A": 50.0, "variant_B": 50.0},
                    "test_dimension": "subject_line",
                }
            ]
        }
    }


class StrategyInputSchema(BaseModel):
    """API-level input for the CampaignStrategyAgent."""

    parsed_brief: ParsedBriefSchema
    segments: list[SegmentOutSchema]
    current_time: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "parsed_brief": {},
                    "segments": [],
                    "current_time": "2026-04-10T09:00:00+00:00",
                }
            ]
        }
    }


class CampaignStrategySchema(BaseModel):
    """Full strategic output of the CampaignStrategyAgent."""

    selected_segments: list[str] = Field(..., description="Segment names selected for targeting")
    send_schedule: dict[str, datetime] = Field(..., description="segment_name → send datetime")
    ab_test_plan: ABTestPlanSchema
    budget_allocation: dict[str, float] = Field(
        ..., description="segment_name → budget percentage (sums to 100)"
    )
    expected_metrics: dict[str, float] = Field(
        ..., description="segment_name → expected open rate (0–1)"
    )
    reasoning: dict[str, str] = Field(default_factory=dict, description="segment_name → rationale")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "selected_segments": ["millennials_active"],
                    "send_schedule": {"millennials_active": "2026-04-11T10:00:00+00:00"},
                    "ab_test_plan": {
                        "num_variants": 2,
                        "variant_distribution": {"variant_A": 50.0, "variant_B": 50.0},
                        "test_dimension": "subject_line",
                    },
                    "budget_allocation": {"millennials_active": 100.0},
                    "expected_metrics": {"millennials_active": 0.28},
                    "reasoning": {"millennials_active": "Highest priority + largest active cohort."},
                }
            ]
        }
    }


# Content Generation ──────────────────────────────────────────────

class ContentGenerationInputSchema(BaseModel):
    """API-level input for the ContentGenerationAgent."""

    parsed_brief: ParsedBriefSchema
    segment: SegmentOutSchema
    variant_id: str = Field(..., min_length=1, description="A/B variant identifier, e.g. 'variant_A'")
    strategy: CampaignStrategySchema

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "parsed_brief": {},
                    "segment": {},
                    "variant_id": "variant_A",
                    "strategy": {},
                }
            ]
        }
    }


class EmailContentSchema(BaseModel):
    """Structured email content output of the ContentGenerationAgent."""

    variant_id: str = Field(..., description="Matches input variant_id")
    segment_name: str = Field(..., description="Target segment name")
    subject_lines: list[str] = Field(..., description="5–10 subject line options (40–60 chars)")
    email_body: str = Field(..., description="Mobile-responsive HTML email body")
    preview_text: str = Field(..., description="50–100 char inbox preview snippet")
    personalization_tags: list[str] = Field(
        default_factory=list, description="Placeholder tokens used in email"
    )
    tone: str = Field("professional", description="Tone applied to the copy")
    estimated_read_time: str = Field("1 min", description="Human-friendly read time")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "variant_id": "variant_A",
                    "segment_name": "millennials_active",
                    "subject_lines": [
                        "[FIRST_NAME], run faster with CloudStorage Pro",
                        "Unlock your potential – CloudStorage Pro is here",
                    ],
                    "email_body": "<!DOCTYPE html>...",
                    "preview_text": "Discover how CloudStorage Pro can transform your workflow today",
                    "personalization_tags": ["[FIRST_NAME]", "[LOCATION]"],
                    "tone": "professional",
                    "estimated_read_time": "1 min",
                }
            ]
        }
    }


# ── Mock Campaign API Schemas ─────────────────────────────────────

class MockAPICustomerResponse(BaseModel):
    """Schema for a single customer returned by GET /api/customers."""

    customer_id: str
    Full_name: str = ""
    email: str = ""
    Age: int = 0
    Gender: str = ""
    Marital_Status: str = ""
    Family_Size: int = 1
    Dependent_count: int = Field(0, alias="Dependent count")
    Occupation: str = ""
    Occupation_type: str = Field("Full-time", alias="Occupation type")
    Monthly_Income: float = 0
    KYC_status: str = Field("N", alias="KYC status")
    City: str = ""
    Kids_in_Household: int = 0
    App_Installed: str = "N"
    Existing_Customer: str = Field("N", alias="Existing Customer")
    Credit_score: int = 300
    Social_Media_Active: str = "N"

    model_config = {"populate_by_name": True}


class MockAPICampaignScheduleRequest(BaseModel):
    """Payload for POST /api/campaigns/schedule."""

    subject_line: str
    email_body: str
    customer_ids: list[str]
    send_time: str = Field(..., description="ISO 8601 datetime")
    campaign_metadata: dict[str, Any] = Field(default_factory=dict)


class MockAPICampaignScheduleResponse(BaseModel):
    """Response from POST /api/campaigns/schedule."""

    campaign_id: str
    status: str
    scheduled_time: str
    customer_count: int


class MockAPIMetricsResponse(BaseModel):
    """Response from GET /api/campaigns/{id}/metrics."""

    campaign_id: str
    open_rate: float = 0.0
    click_rate: float = 0.0
    click_through_rate: float = 0.0
    total_sent: int = 0
    unique_opens: int = 0
    unique_clicks: int = 0


class MockAPICustomerResultResponse(BaseModel):
    """Response from GET /api/campaigns/{id}/results."""

    campaign_id: str
    customer_results: list[dict[str, Any]] = Field(default_factory=list)


class MockAPIValidateRequest(BaseModel):
    """Payload for POST /api/campaigns/validate."""

    subject_line: str
    email_body: str
    customer_ids: list[str]


class MockAPIValidateResponse(BaseModel):
    """Response from POST /api/campaigns/validate."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
