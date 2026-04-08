"""Shared pytest fixtures for database testing."""

import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.models.campaign import Campaign, CampaignStatus, ParsedData
from app.models.customer import (
    ActivityStatus,
    Customer,
    Gender,
    Preferences,
    PurchaseRecord,
)
from app.models.metrics import Metrics
from app.models.segment import Segment, SegmentCriteria
from app.models.variant import CampaignVariant, VariantStatus


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def mock_db():
    """Provide a fresh in-memory MongoDB database per test."""
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    yield db
    client.close()


# ── Sample data factories ────────────────────────────────────────


@pytest.fixture
def sample_customer() -> Customer:
    return Customer(
        customer_id="cust-001",
        age=30,
        gender=Gender.MALE,
        location="New York",
        activity_status=ActivityStatus.ACTIVE,
        purchase_history=[
            PurchaseRecord(product="Laptop", amount=999.99, date=datetime(2024, 1, 15)),
        ],
        preferences=Preferences(tags=["tech", "gadgets"], categories=["Electronics"]),
    )


@pytest.fixture
def sample_customers() -> list[Customer]:
    """Return a list of 5 diverse customers."""
    return [
        Customer(
            customer_id=f"cust-{i:03d}",
            age=age,
            gender=gender,
            location=location,
            activity_status=status,
            purchase_history=[
                PurchaseRecord(product="Item", amount=50.0, date=datetime(2024, 1, 1)),
            ],
        )
        for i, (age, gender, location, status) in enumerate(
            [
                (25, Gender.FEMALE, "Chicago", ActivityStatus.ACTIVE),
                (40, Gender.MALE, "Houston", ActivityStatus.INACTIVE),
                (35, Gender.OTHER, "Chicago", ActivityStatus.ACTIVE),
                (55, Gender.FEMALE, "New York", ActivityStatus.DORMANT),
                (22, Gender.MALE, "Los Angeles", ActivityStatus.ACTIVE),
            ],
            start=1,
        )
    ]


@pytest.fixture
def sample_campaign() -> Campaign:
    return Campaign(
        campaign_id="camp-001",
        campaign_brief="Launch the new Running Shoes Pro X with a 20% discount",
        parsed_data=ParsedData(
            product_name="Running Shoes Pro X",
            target_audience="Fitness enthusiasts aged 18-45",
            campaign_goal="Increase product sales by 30%",
            budget=5000.00,
        ),
        status=CampaignStatus.DRAFT,
        created_by="admin",
    )


@pytest.fixture
def sample_campaigns() -> list[Campaign]:
    """Return campaigns in several statuses."""
    configs = [
        ("camp-001", "Brief for campaign 1", CampaignStatus.DRAFT),
        ("camp-002", "Brief for campaign 2", CampaignStatus.PENDING_APPROVAL),
        ("camp-003", "Brief for campaign 3", CampaignStatus.APPROVED),
        ("camp-004", "Brief for campaign 4", CampaignStatus.EXECUTING),
        ("camp-005", "Brief for campaign 5", CampaignStatus.OPTIMIZING),
        ("camp-006", "Brief for campaign 6", CampaignStatus.COMPLETED),
    ]
    return [
        Campaign(
            campaign_id=cid,
            campaign_brief=brief,
            status=status,
            parsed_data=ParsedData(product_name=f"Product {cid[-1]}"),
        )
        for cid, brief, status in configs
    ]


@pytest.fixture
def sample_variant() -> CampaignVariant:
    return CampaignVariant(
        variant_id="var-001",
        campaign_id="camp-001",
        segment_name="young_active",
        subject_line="Get 20% off Running Shoes!",
        email_body="A" * 60,  # meets min 50 chars
        status=VariantStatus.DRAFT,
        personalization_tags=["first_name", "location"],
    )


@pytest.fixture
def sample_variants() -> list[CampaignVariant]:
    """Return variants across two campaigns and segments."""
    now = datetime.utcnow()
    return [
        CampaignVariant(
            variant_id="var-001",
            campaign_id="camp-001",
            segment_name="young_active",
            subject_line="Subject A",
            email_body="B" * 60,
            status=VariantStatus.DRAFT,
        ),
        CampaignVariant(
            variant_id="var-002",
            campaign_id="camp-001",
            segment_name="high_spenders",
            subject_line="Subject B",
            email_body="C" * 60,
            status=VariantStatus.SCHEDULED,
            send_time=now + timedelta(hours=2),
        ),
        CampaignVariant(
            variant_id="var-003",
            campaign_id="camp-002",
            segment_name="young_active",
            subject_line="Subject C",
            email_body="D" * 60,
            status=VariantStatus.SCHEDULED,
            send_time=now + timedelta(hours=5),
        ),
        CampaignVariant(
            variant_id="var-004",
            campaign_id="camp-002",
            segment_name="dormant_users",
            subject_line="Subject D",
            email_body="E" * 60,
            status=VariantStatus.SENT,
        ),
    ]


@pytest.fixture
def sample_metrics() -> Metrics:
    return Metrics(
        metric_id="met-001",
        variant_id="var-001",
        campaign_id="camp-001",
        open_rate=35.0,
        click_rate=8.5,
        emails_sent=1000,
        emails_opened=350,
        emails_clicked=85,
    )


@pytest.fixture
def sample_metrics_list() -> list[Metrics]:
    """Return metrics for two campaigns, variant performance varies."""
    return [
        Metrics(
            metric_id="met-001",
            variant_id="var-001",
            campaign_id="camp-001",
            open_rate=40.0,
            click_rate=10.0,
            emails_sent=1000,
            emails_opened=400,
            emails_clicked=100,
        ),
        Metrics(
            metric_id="met-002",
            variant_id="var-002",
            campaign_id="camp-001",
            open_rate=20.0,
            click_rate=3.0,
            emails_sent=800,
            emails_opened=160,
            emails_clicked=24,
        ),
        Metrics(
            metric_id="met-003",
            variant_id="var-003",
            campaign_id="camp-002",
            open_rate=50.0,
            click_rate=15.0,
            emails_sent=500,
            emails_opened=250,
            emails_clicked=75,
        ),
    ]


@pytest.fixture
def sample_segment() -> Segment:
    return Segment(
        segment_id="seg-001",
        campaign_id="camp-001",
        segment_name="young_active",
        description="Active customers aged 18-35",
        customer_ids=["cust-001", "cust-002", "cust-003"],
        segment_criteria=SegmentCriteria(
            age_range=[18, 35],
            activity_status=["active"],
        ),
    )
