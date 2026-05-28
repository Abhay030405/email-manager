"""Unit tests for the Campaign model."""

import pytest

from app.models.campaign import Campaign, CampaignStatus, ParsedData


@pytest.mark.unit
class TestCampaignModel:

    def test_create_campaign_with_defaults(self):
        c = Campaign(
            campaign_id="camp-001",
            campaign_brief="Test brief",
            parsed_data=ParsedData(product_name="TestProduct", campaign_goal="awareness"),
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
        pd = ParsedData(product_name="MyProduct")
        assert pd.product_name == "MyProduct"
        assert pd.campaign_goal == "awareness"
        assert pd.cta_link is None or pd.cta_link == ""

    def test_campaign_model_dump(self):
        c = Campaign(
            campaign_id="camp-002",
            campaign_brief="Brief",
            parsed_data=ParsedData(product_name="P", campaign_goal="conversion"),
        )
        d = c.model_dump()
        assert d["campaign_id"] == "camp-002"
        assert d["status"] == "draft"
        assert "parsed_data" in d

    def test_campaign_brief_required(self):
        with pytest.raises(Exception):
            Campaign(campaign_id="x", parsed_data=ParsedData(product_name="P"))

    def test_campaign_id_required(self):
        with pytest.raises(Exception):
            Campaign(
                campaign_brief="brief",
                parsed_data=ParsedData(product_name="P"),
            )
