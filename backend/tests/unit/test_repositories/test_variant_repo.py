"""Unit tests for VariantRepository."""

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.variant_repo import VariantRepository
from app.models.variant import CampaignVariant, VariantStatus


@pytest_asyncio.fixture
async def variant_repo():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    yield VariantRepository(db)
    client.close()


def _make_variant(variant_id: str = "var-001", campaign_id: str = "camp-001", **kw) -> CampaignVariant:
    return CampaignVariant(
        variant_id=variant_id,
        campaign_id=campaign_id,
        segment_name=kw.get("segment_name", "test_segment"),
        subject_line="Test Subject",
        email_body="Test body content.",
        status=kw.get("status", VariantStatus.DRAFT),
        customer_ids=kw.get("customer_ids", ["CUST0001"]),
    )


@pytest.mark.unit
class TestVariantRepository:

    @pytest.mark.asyncio
    async def test_create_variant(self, variant_repo):
        variant = _make_variant("var-create-01")
        result = await variant_repo.create(variant)
        assert result.variant_id == "var-create-01"

    @pytest.mark.asyncio
    async def test_find_by_id(self, variant_repo):
        variant = _make_variant("var-find-01")
        await variant_repo.create(variant)
        found = await variant_repo.find_by_id("var-find-01")
        assert found is not None

    @pytest.mark.asyncio
    async def test_find_by_campaign(self, variant_repo):
        await variant_repo.create(_make_variant("var-c1-1", campaign_id="camp-c1"))
        await variant_repo.create(_make_variant("var-c1-2", campaign_id="camp-c1"))
        await variant_repo.create(_make_variant("var-c2-1", campaign_id="camp-c2"))

        results = await variant_repo.find_by_campaign("camp-c1")
        assert len(results) == 2
        assert all(v.campaign_id == "camp-c1" for v in results)

    @pytest.mark.asyncio
    async def test_find_by_segment(self, variant_repo):
        await variant_repo.create(_make_variant("var-seg-1", segment_name="young_pros"))
        await variant_repo.create(_make_variant("var-seg-2", segment_name="seniors"))

        results = await variant_repo.find_by_segment("young_pros")
        assert len(results) == 1
        assert results[0].segment_name == "young_pros"

    @pytest.mark.asyncio
    async def test_update_status_bulk(self, variant_repo):
        for vid in ("var-bulk-1", "var-bulk-2", "var-bulk-3"):
            await variant_repo.create(_make_variant(vid))

        updated = await variant_repo.update_status_bulk(
            ["var-bulk-1", "var-bulk-2"],
            VariantStatus.SCHEDULED,
        )
        assert updated == 2

    @pytest.mark.asyncio
    async def test_delete_variant(self, variant_repo):
        await variant_repo.create(_make_variant("var-del-01"))
        deleted = await variant_repo.delete("var-del-01")
        assert deleted is True
        assert await variant_repo.find_by_id("var-del-01") is None
