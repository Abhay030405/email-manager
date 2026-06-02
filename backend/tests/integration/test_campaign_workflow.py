"""Integration tests for campaign creation workflow."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.variant_repo import VariantRepository
from app.db.repositories.customer_repo import CustomerRepository
from app.models.campaign import Campaign, CampaignStatus, ParsedData
from app.models.customer import Customer
from app.models.variant import CampaignVariant, VariantStatus


@pytest_asyncio.fixture
async def db():
    client = AsyncMongoMockClient()
    yield client["campaignx_test"]
    client.close()


@pytest_asyncio.fixture
async def repos(db):
    return {
        "campaign": CampaignRepository(db),
        "variant": VariantRepository(db),
        "customer": CustomerRepository(db),
    }


@pytest_asyncio.fixture
async def seeded_campaign(repos):
    campaign = Campaign(
        campaign_id="camp-int-001",
        campaign_brief="Promote XDeposit to young professionals",
        parsed_data=ParsedData(
            product_details={"product_name": "XDeposit", "product_description": "", "cta_link": ""},
            target_audience={"Group 1": {"min_age": 25, "max_age": 35}},
            campaign_goal={"objective": "conversion"},
        ),
        status=CampaignStatus.DRAFT,
    )
    return await repos["campaign"].create(campaign)


@pytest.mark.integration
class TestCampaignWorkflowIntegration:

    @pytest.mark.asyncio
    async def test_campaign_created_with_draft_status(self, repos):
        campaign = Campaign(
            campaign_id="camp-wf-001",
            campaign_brief="Test integration campaign",
            parsed_data=ParsedData(
                product_details={"product_name": "TestProduct", "product_description": "", "cta_link": ""},
                campaign_goal={"objective": "awareness"},
            ),
            status=CampaignStatus.DRAFT,
        )

        created = await repos["campaign"].create(campaign)

        assert created.campaign_id == "camp-wf-001"
        assert created.status == CampaignStatus.DRAFT

    @pytest.mark.asyncio
    async def test_campaign_status_transitions(self, repos, seeded_campaign):
        cid = seeded_campaign.campaign_id

        updated = await repos["campaign"].update_status(cid, CampaignStatus.PENDING_APPROVAL)
        assert updated.status == CampaignStatus.PENDING_APPROVAL

        approved = await repos["campaign"].update_status(cid, CampaignStatus.APPROVED)
        assert approved.status == CampaignStatus.APPROVED

        executing = await repos["campaign"].update_status(cid, CampaignStatus.EXECUTING)
        assert executing.status == CampaignStatus.EXECUTING

        completed = await repos["campaign"].update_status(cid, CampaignStatus.COMPLETED)
        assert completed.status == CampaignStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_variants_linked_to_campaign(self, repos, seeded_campaign):
        cid = seeded_campaign.campaign_id

        for i in range(3):
            variant = CampaignVariant(
                variant_id=f"var-wf-{i:02d}",
                campaign_id=cid,
                segment_name=f"segment_{i}",
                subject_line=f"Subject variant {i}",
                email_body=f"Body variant {i}",
                status=VariantStatus.DRAFT,
                customer_ids=[f"CUST{i:04d}"],
            )
            await repos["variant"].create(variant)

        variants = await repos["variant"].find_by_campaign(cid)
        assert len(variants) == 3
        assert all(v.campaign_id == cid for v in variants)

    @pytest.mark.asyncio
    async def test_campaign_with_variants_aggregate(self, repos, seeded_campaign):
        cid = seeded_campaign.campaign_id

        variant = CampaignVariant(
            variant_id="var-agg-01",
            campaign_id=cid,
            segment_name="test_seg",
            subject_line="Aggregate test",
            email_body="Body",
            status=VariantStatus.DRAFT,
            customer_ids=["CUST0001"],
        )
        await repos["variant"].create(variant)

        result = await repos["campaign"].get_campaign_with_variants(cid)
        assert result is not None
        assert "variants" in result
        assert len(result["variants"]) >= 1

    @pytest.mark.asyncio
    async def test_customers_synced_and_queryable(self, repos):
        customers = [
            Customer(
                customer_id=f"CUST{100 + i:04d}",
                Full_name=f"Customer {i}",
                email=f"cust{i}@example.com",
                Age=25 + i,
                Gender="Male",
                Marital_Status="Single",
                Family_Size=1,
                Dependent_count=0,
                Occupation="Engineer",
                Occupation_type="Full-time",
                Monthly_Income=60000 + i * 5000,
                KYC_status="Y",
                City="Bangalore",
                Kids_in_Household=0,
                App_Installed="Y",
                Existing_Customer="N",
                Credit_score=700 + i,
                Social_Media_Active="Y",
                synced_from_mock_api=True,
            )
            for i in range(5)
        ]

        count = await repos["customer"].bulk_insert(customers)
        assert count == 5

        total = await repos["customer"].count()
        assert total >= 5
