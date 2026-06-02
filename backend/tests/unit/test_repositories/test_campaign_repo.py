"""Unit tests for CampaignRepository (using in-memory mongomock)."""

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.campaign_repo import CampaignRepository
from app.models.campaign import Campaign, CampaignStatus, ParsedData


@pytest_asyncio.fixture
async def campaign_repo():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    yield CampaignRepository(db)
    client.close()


def _make_campaign(campaign_id: str = "camp-001", **kwargs) -> Campaign:
    return Campaign(
        campaign_id=campaign_id,
        campaign_brief=kwargs.get("campaign_brief", "Test campaign brief"),
        parsed_data=ParsedData(
            product_details={"product_name": kwargs.get("product_name", "TestProduct"), "product_description": "", "cta_link": ""},
            campaign_goal={"objective": kwargs.get("campaign_goal", "awareness")},
        ),
        status=kwargs.get("status", CampaignStatus.DRAFT),
    )


@pytest.mark.unit
class TestCampaignRepository:

    @pytest.mark.asyncio
    async def test_create_campaign(self, campaign_repo):
        campaign = _make_campaign("camp-create-01")
        result = await campaign_repo.create(campaign)

        assert result.campaign_id == "camp-create-01"
        assert result.status == CampaignStatus.DRAFT

    @pytest.mark.asyncio
    async def test_find_by_id(self, campaign_repo):
        campaign = _make_campaign("camp-find-01")
        await campaign_repo.create(campaign)

        found = await campaign_repo.find_by_id("camp-find-01")
        assert found is not None
        assert found.campaign_id == "camp-find-01"

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, campaign_repo):
        result = await campaign_repo.find_by_id("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_all_empty(self, campaign_repo):
        results = await campaign_repo.find_all()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_find_all_with_data(self, campaign_repo):
        for i in range(3):
            await campaign_repo.create(_make_campaign(f"camp-list-{i}"))

        results = await campaign_repo.find_all()
        assert len(results) >= 3

    @pytest.mark.asyncio
    async def test_update_campaign(self, campaign_repo):
        campaign = _make_campaign("camp-update-01")
        await campaign_repo.create(campaign)

        updated = await campaign_repo.update(
            "camp-update-01",
            {"campaign_brief": "Updated brief"}
        )

        assert updated is not None
        assert updated.campaign_brief == "Updated brief"

    @pytest.mark.asyncio
    async def test_update_non_existent_returns_none(self, campaign_repo):
        result = await campaign_repo.update("ghost-id", {"campaign_brief": "x"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_campaign(self, campaign_repo):
        campaign = _make_campaign("camp-delete-01")
        await campaign_repo.create(campaign)

        deleted = await campaign_repo.delete("camp-delete-01")
        assert deleted is True

        found = await campaign_repo.find_by_id("camp-delete-01")
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_non_existent_returns_false(self, campaign_repo):
        result = await campaign_repo.delete("ghost-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_count(self, campaign_repo):
        for i in range(4):
            await campaign_repo.create(_make_campaign(f"camp-count-{i}"))

        total = await campaign_repo.count()
        assert total >= 4

    @pytest.mark.asyncio
    async def test_update_status(self, campaign_repo):
        campaign = _make_campaign("camp-status-01")
        await campaign_repo.create(campaign)

        updated = await campaign_repo.update_status(
            "camp-status-01", CampaignStatus.APPROVED
        )

        assert updated is not None
        assert updated.status == CampaignStatus.APPROVED

    @pytest.mark.asyncio
    async def test_find_by_status(self, campaign_repo):
        await campaign_repo.create(_make_campaign("camp-stat-1", status=CampaignStatus.DRAFT))
        await campaign_repo.create(_make_campaign("camp-stat-2", status=CampaignStatus.APPROVED))

        drafts = await campaign_repo.find_by_status("draft")
        assert any(c.campaign_id == "camp-stat-1" for c in drafts)

    @pytest.mark.asyncio
    async def test_find_pending_approval(self, campaign_repo):
        await campaign_repo.create(
            _make_campaign("camp-pending-1", status=CampaignStatus.PENDING_APPROVAL)
        )

        pending = await campaign_repo.find_pending_approval()
        assert any(c.campaign_id == "camp-pending-1" for c in pending)

    @pytest.mark.asyncio
    async def test_bulk_insert(self, campaign_repo):
        campaigns = [_make_campaign(f"camp-bulk-{i}") for i in range(5)]
        count = await campaign_repo.bulk_insert(campaigns)
        assert count == 5
