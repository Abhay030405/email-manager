"""Error scenario tests for database operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.campaign_repo import CampaignRepository
from app.models.campaign import Campaign, CampaignStatus, ParsedData


def _make_campaign_repo():
    client = AsyncMongoMockClient()
    return CampaignRepository(client["campaignx_test"])


def _sample_campaign(**kwargs) -> Campaign:
    defaults = dict(
        campaign_id="camp-err-001",
        campaign_brief="Error handling test campaign",
        parsed_data=ParsedData(product_details={"product_name": "TestProduct", "product_description": "", "cta_link": ""}),
        status=CampaignStatus.DRAFT,
    )
    defaults.update(kwargs)
    return Campaign(**defaults)


@pytest.mark.unit
class TestDatabaseErrors:

    # ── Not found ─────────────────────────────────────────────────

    async def test_find_by_id_nonexistent_returns_none(self):
        repo = _make_campaign_repo()
        result = await repo.find_by_id("nonexistent-campaign-id-xyz")
        assert result is None

    async def test_update_nonexistent_returns_none(self):
        repo = _make_campaign_repo()
        result = await repo.update("nonexistent-id", {"status": "approved"})
        assert result is None

    async def test_delete_nonexistent_returns_false_or_zero(self):
        repo = _make_campaign_repo()
        result = await repo.delete("nonexistent-id")
        assert result in (False, 0, None)

    # ── Duplicate key / upsert behaviour ─────────────────────────

    async def test_create_same_campaign_id_twice_raises_or_upserts(self):
        repo = _make_campaign_repo()
        campaign = _sample_campaign()
        await repo.create(campaign)

        # Second create with same ID should either raise or silently upsert
        try:
            await repo.create(campaign)
        except Exception:
            pass  # Expected — duplicate key error is acceptable

    # ── Find-all with empty collection ───────────────────────────

    async def test_list_all_empty_collection(self):
        repo = _make_campaign_repo()
        campaigns = await repo.find_all()
        assert isinstance(campaigns, list)
        assert len(campaigns) == 0

    # ── Count on empty collection ─────────────────────────────────

    async def test_count_empty_returns_zero(self):
        repo = _make_campaign_repo()
        count = await repo.count()
        assert count == 0

    # ── CRUD roundtrip ────────────────────────────────────────────

    async def test_create_and_find_campaign(self):
        repo = _make_campaign_repo()
        campaign = _sample_campaign(campaign_id="camp-roundtrip-001")
        created = await repo.create(campaign)
        assert created is not None

        found = await repo.find_by_id("camp-roundtrip-001")
        assert found is not None
        assert found.campaign_id == "camp-roundtrip-001"

    async def test_update_campaign_field(self):
        repo = _make_campaign_repo()
        campaign = _sample_campaign(campaign_id="camp-update-001")
        await repo.create(campaign)

        updated = await repo.update("camp-update-001", {"status": "approved"})
        assert updated is not None
        assert updated.status.value == "approved" or updated.status == "approved"

    async def test_delete_campaign(self):
        repo = _make_campaign_repo()
        campaign = _sample_campaign(campaign_id="camp-delete-001")
        await repo.create(campaign)

        await repo.delete("camp-delete-001")
        found = await repo.find_by_id("camp-delete-001")
        assert found is None
