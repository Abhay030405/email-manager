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
    }


@pytest.fixture
def sample_parsed_data() -> dict:
    return {
        "product_details": {
            "product_name": "XDeposit",
            "product_description": "High-yield savings account with flexible terms",
            "cta_link": "https://example.com/xdeposit",
        },
        "target_audience": {
            "Group 1": {"min_age": 25, "max_age": 35, "Occupation": "Professional"},
        },
        "campaign_goal": {"objective": "Drive sign-ups / conversions"},
        "campaign_preferences": {
            "email_tone": "Friendly",
            "campaign_name": "XDeposit Launch",
            "content_hints": "1% higher returns than market average",
        },
    }


@pytest.fixture
def sample_campaign() -> Campaign:
    return Campaign(
        campaign_id="camp-test-001",
        campaign_brief="Promote XDeposit to young professionals",
        parsed_data=ParsedData(
            product_details={"product_name": "XDeposit", "product_description": "High-yield savings account", "cta_link": "https://example.com/xdeposit"},
            target_audience={"Group 1": {"min_age": 25, "max_age": 35, "Occupation": "Professional"}},
            campaign_goal={"objective": "Drive sign-ups / conversions"},
        ),
        status=CampaignStatus.DRAFT,
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
            parsed_data=ParsedData(
                product_details={"product_name": f"Product {i}", "product_description": "", "cta_link": ""},
                campaign_goal={"objective": "awareness"},
            ),
            status=status,
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
