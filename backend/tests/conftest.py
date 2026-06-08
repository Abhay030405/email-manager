"""Shared pytest fixtures for database testing.

Updated for Mock Campaign API customer schema (18-field Indian demographics).
"""

import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.models.campaign import Campaign, CampaignStatus, ParsedData
from app.models.customer import Customer
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
        customer_id="CUST0001",
        Full_name="Ravi Sharma",
        email="ravi.sharma@example.com",
        Age=30,
        Gender="Male",
        Marital_Status="Married",
        Family_Size=4,
        Dependent_count=2,
        Occupation="Software Engineer",
        Occupation_type="Full-time",
        Monthly_Income=85000.0,
        KYC_status="Y",
        City="Mumbai",
        Kids_in_Household=1,
        App_Installed="Y",
        Existing_Customer="Y",
        Credit_score=750,
        Social_Media_Active="Y",
        synced_from_mock_api=True,
    )


@pytest.fixture
def sample_customers() -> list[Customer]:
    """Return a list of 5 diverse customers matching Mock API schema."""
    return [
        Customer(
            customer_id=f"CUST{i:04d}",
            Full_name=name,
            email=f"{name.lower().replace(' ', '.')}@example.com",
            Age=age,
            Gender=gender,
            Marital_Status=marital,
            City=city,
            Occupation_type=occ_type,
            Monthly_Income=income,
            Credit_score=credit,
            App_Installed=app,
            Existing_Customer=existing,
            Social_Media_Active=social,
            Family_Size=fam,
            Dependent_count=dep,
            Occupation=occ,
            KYC_status=kyc,
            Kids_in_Household=kids,
        )
        for i, (name, age, gender, marital, city, occ_type, income, credit, app, existing, social, fam, dep, occ, kyc, kids) in enumerate(
            [
                ("Priya Patel", 25, "Female", "Single", "Kolkata", "Full-time", 55000, 680, "Y", "Y", "Y", 3, 0, "Software Engineer", "Y", 0),
                ("Amit Kumar", 40, "Male", "Married", "Delhi", "Self-employed", 120000, 790, "N", "Y", "N", 5, 2, "Business Owner", "Y", 1),
                ("Sanjay Verma", 35, "Other", "Single", "Kolkata", "Part-time", 30000, 620, "Y", "N", "Y", 2, 0, "Freelancer", "N", 0),
                ("Meena Devi", 55, "Female", "Widowed", "Mumbai", "Retired", 25000, 710, "N", "Y", "N", 4, 1, "Homemaker", "Y", 0),
                ("Rahul Singh", 22, "Male", "Single", "Bangalore", "Student", 10000, 550, "Y", "N", "Y", 3, 0, "Student", "N", 0),
            ],
            start=1,
        )
    ]


@pytest.fixture
def sample_campaign() -> Campaign:
    return Campaign(
        campaign_id="camp-001",
        campaign_brief="Launch Diwali sale for premium electronics targeting urban males",
        parsed_data=ParsedData(
            product_details={"product_name": "Premium Electronics Diwali Offer", "product_description": "", "cta_link": ""},
            target_audience={"Group 1": {"min_age": 25, "max_age": 40, "Occupation": "Professional"}},
            campaign_goal={"objective": "Drive 15% conversion rate"},
        ),
        status=CampaignStatus.DRAFT,
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
            parsed_data=ParsedData(product_details={"product_name": f"Product {cid[-1]}", "product_description": "", "cta_link": ""}),
        )
        for cid, brief, status in configs
    ]


@pytest.fixture
def sample_variant() -> CampaignVariant:
    return CampaignVariant(
        variant_id="var-001",
        campaign_id="camp-001",
        segment_name="young_active",
        subject_line="Get 20% off this Diwali!",
        email_body="<p>Exclusive Diwali deals on premium electronics.</p>",
        status=VariantStatus.DRAFT,
        personalization_tags=["Full_name", "City"],
        customer_ids=["CUST0001", "CUST0002"],
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
            email_body="Body of variant A",
            status=VariantStatus.DRAFT,
            customer_ids=["CUST0001"],
        ),
        CampaignVariant(
            variant_id="var-002",
            campaign_id="camp-001",
            segment_name="high_spenders",
            subject_line="Subject B",
            email_body="Body of variant B",
            status=VariantStatus.SCHEDULED,
            send_time=now + timedelta(hours=2),
            customer_ids=["CUST0002", "CUST0003"],
        ),
        CampaignVariant(
            variant_id="var-003",
            campaign_id="camp-002",
            segment_name="young_active",
            subject_line="Subject C",
            email_body="Body of variant C",
            status=VariantStatus.SCHEDULED,
            send_time=now + timedelta(hours=5),
            customer_ids=["CUST0004"],
        ),
        CampaignVariant(
            variant_id="var-004",
            campaign_id="camp-002",
            segment_name="dormant_users",
            subject_line="Subject D",
            email_body="Body of variant D",
            status=VariantStatus.SENT,
        ),
    ]


@pytest.fixture
def sample_metrics() -> Metrics:
    return Metrics(
        metric_id="met-001",
        variant_id="var-001",
        campaign_id="camp-001",
        mock_campaign_id="mock-001",
        open_rate=0.35,
        click_rate=0.085,
        click_through_rate=0.06,
        total_sent=1000,
        unique_opens=350,
        unique_clicks=85,
    )


@pytest.fixture
def sample_metrics_list() -> list[Metrics]:
    """Return metrics for two campaigns, variant performance varies."""
    return [
        Metrics(
            metric_id="met-001",
            variant_id="var-001",
            campaign_id="camp-001",
            mock_campaign_id="mock-001",
            open_rate=0.40,
            click_rate=0.10,
            click_through_rate=0.07,
            total_sent=1000,
            unique_opens=400,
            unique_clicks=100,
        ),
        Metrics(
            metric_id="met-002",
            variant_id="var-002",
            campaign_id="camp-001",
            mock_campaign_id="mock-002",
            open_rate=0.20,
            click_rate=0.03,
            click_through_rate=0.02,
            total_sent=800,
            unique_opens=160,
            unique_clicks=24,
        ),
        Metrics(
            metric_id="met-003",
            variant_id="var-003",
            campaign_id="camp-002",
            mock_campaign_id="mock-003",
            open_rate=0.50,
            click_rate=0.15,
            click_through_rate=0.10,
            total_sent=500,
            unique_opens=250,
            unique_clicks=75,
        ),
    ]


@pytest.fixture
def sample_segment() -> Segment:
    return Segment(
        segment_id="seg-001",
        campaign_id="camp-001",
        segment_name="young_active",
        description="Active young customers in metro cities",
        customer_ids=["CUST0001", "CUST0002", "CUST0003"],
        segment_criteria=SegmentCriteria(
            age_range={"min": 18, "max": 35},
            app_installed="Y",
        ),
    )
