"""Campaign test data fixtures."""

from datetime import datetime, timedelta

import pytest

from app.models.campaign import Campaign, CampaignStatus, ParsedData
from app.models.variant import CampaignVariant, VariantStatus


@pytest.fixture
def sample_campaign_brief() -> str:
    return (
        "Promote XDeposit savings account to young professionals (25-35) "
        "with personalized recommendations for higher returns."
    )


@pytest.fixture
def sample_campaign_create_payload() -> dict:
    return {
        "campaign_brief": (
            "Promote XDeposit savings account to young professionals (25-35) "
            "with personalized recommendations for higher returns."
        ),
        "created_by": "test_user",
    }


@pytest.fixture
def sample_parsed_data() -> dict:
    return {
        "product_name": "XDeposit",
        "product_description": "High-yield savings account with flexible terms",
        "target_audience": "Young professionals aged 25-35",
        "campaign_goal": "conversion",
        "cta_link": "https://example.com/xdeposit",
        "budget": 50000.0,
        "preferred_tone": "professional",
        "key_messages": [
            "1% higher returns than market average",
            "Flexible withdrawal terms",
            "No minimum balance required",
        ],
        "constraints": None,
    }


@pytest.fixture
def sample_campaign() -> Campaign:
    return Campaign(
        campaign_id="camp-test-001",
        campaign_brief="Promote XDeposit to young professionals",
        parsed_data=ParsedData(
            product_name="XDeposit",
            target_audience="Young professionals aged 25-35",
            campaign_goal="conversion",
            cta_link="https://example.com/xdeposit",
            budget=50000.0,
        ),
        status=CampaignStatus.DRAFT,
        created_by="test_user",
    )


@pytest.fixture
def sample_campaigns() -> list[Campaign]:
    statuses = [
        CampaignStatus.DRAFT,
        CampaignStatus.PENDING_APPROVAL,
        CampaignStatus.APPROVED,
        CampaignStatus.EXECUTING,
        CampaignStatus.COMPLETED,
    ]
    return [
        Campaign(
            campaign_id=f"camp-test-{i:03d}",
            campaign_brief=f"Campaign brief {i}",
            parsed_data=ParsedData(product_name=f"Product {i}", campaign_goal="awareness"),
            status=status,
            created_by="test_user",
        )
        for i, status in enumerate(statuses, 1)
    ]


@pytest.fixture
def sample_segments() -> dict:
    return {
        "segment_young_professionals": ["CUST0001", "CUST0002", "CUST0003"],
        "segment_seniors": ["CUST0004", "CUST0005"],
        "segment_students": ["CUST0006", "CUST0007"],
    }


@pytest.fixture
def sample_variants() -> list[CampaignVariant]:
    now = datetime.utcnow()
    return [
        CampaignVariant(
            variant_id="var-test-001",
            campaign_id="camp-test-001",
            segment_name="segment_young_professionals",
            subject_line="Unlock 1% Higher Returns - Exclusive Offer Inside",
            email_body="Dear Customer,\n\nDiscover XDeposit...",
            send_time=now + timedelta(hours=1),
            status=VariantStatus.DRAFT,
            customer_ids=["CUST0001", "CUST0002", "CUST0003"],
        ),
        CampaignVariant(
            variant_id="var-test-002",
            campaign_id="camp-test-001",
            segment_name="segment_seniors",
            subject_line="Safe, Secure Returns - Your Money Growing",
            email_body="Dear Valued Customer...",
            send_time=now + timedelta(hours=1),
            status=VariantStatus.DRAFT,
            customer_ids=["CUST0004", "CUST0005"],
        ),
    ]
