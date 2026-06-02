"""Unit tests for the Campaign model."""

import pytest

from app.models.campaign import Campaign, CampaignStatus, ParsedData


@pytest.mark.unit
class TestCampaignModel:

    def test_create_campaign_with_defaults(self):
        c = Campaign(
            campaign_id="camp-001",
            campaign_brief="Test brief",
            parsed_data=ParsedData(
                product_details={"product_name": "TestProduct", "product_description": "", "cta_link": ""},
                campaign_goal={"objective": "awareness"},
            ),
        )
        assert c.campaign_id == "camp-001"
        assert c.status == CampaignStatus.DRAFT
        assert c.created_at is not None
        assert c.updated_at is not None

    def test_campaign_status_enum_values(self):
        assert CampaignStatus.DRAFT == "draft"
        assert CampaignStatus.PENDING_APPROVAL == "pending_approval"
        assert CampaignStatus.APPROVED == "approved"
        assert CampaignStatus.EXECUTING == "executing"
        assert CampaignStatus.COMPLETED == "completed"
        assert CampaignStatus.OPTIMIZING == "optimizing"
        assert CampaignStatus.REJECTED == "rejected"

    def test_parsed_data_defaults(self):
        pd = ParsedData()
        assert pd.product_details.product_name == ""
        assert pd.campaign_goal.objective == ""
        assert pd.target_audience == {}

    def test_campaign_model_dump(self):
        c = Campaign(
            campaign_id="camp-002",
            campaign_brief="Brief",
            parsed_data=ParsedData(
                product_details={"product_name": "P", "product_description": "", "cta_link": ""},
                campaign_goal={"objective": "conversion"},
            ),
        )
        d = c.model_dump()
        assert d["campaign_id"] == "camp-002"
        assert d["status"] == "draft"
        assert "parsed_data" in d
        assert d["parsed_data"]["product_details"]["product_name"] == "P"

    def test_campaign_brief_required(self):
        with pytest.raises(Exception):
            Campaign(campaign_id="x")

    def test_campaign_id_auto_generated_when_omitted(self):
        c = Campaign(campaign_brief="brief")
        assert c.campaign_id is not None
        assert len(c.campaign_id) > 0
