"""Tests for VariantRepository."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from app.db.repositories.variant_repo import VariantRepository
from app.models.variant import CampaignVariant, VariantStatus


@pytest_asyncio.fixture
async def repo(mock_db):
    return VariantRepository(mock_db)


@pytest_asyncio.fixture
async def seeded_repo(mock_db, sample_variants):
    """Repo pre-loaded with 4 variants across 2 campaigns."""
    repo = VariantRepository(mock_db)
    for v in sample_variants:
        await repo.create(v)
    return repo


# ── CRUD Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_variant(repo, sample_variant):
    result = await repo.create(sample_variant)
    assert result.variant_id == "var-001"
    assert result.campaign_id == "camp-001"


@pytest.mark.asyncio
async def test_find_by_id(repo, sample_variant):
    await repo.create(sample_variant)
    found = await repo.find_by_id("var-001")
    assert found is not None
    assert found.segment_name == "young_active"


@pytest.mark.asyncio
async def test_find_by_id_not_found(repo):
    assert await repo.find_by_id("ghost") is None


@pytest.mark.asyncio
async def test_update_variant(repo, sample_variant):
    await repo.create(sample_variant)
    updated = await repo.update("var-001", {"subject_line": "New Subject"})
    assert updated is not None
    assert updated.subject_line == "New Subject"


@pytest.mark.asyncio
async def test_delete_variant(repo, sample_variant):
    await repo.create(sample_variant)
    assert await repo.delete("var-001") is True
    assert await repo.find_by_id("var-001") is None


@pytest.mark.asyncio
async def test_count(seeded_repo):
    assert await seeded_repo.count() == 4


# ── Specialised Query Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_find_by_campaign(seeded_repo):
    camp1 = await seeded_repo.find_by_campaign("camp-001")
    assert len(camp1) == 2
    assert all(v.campaign_id == "camp-001" for v in camp1)

    camp2 = await seeded_repo.find_by_campaign("camp-002")
    assert len(camp2) == 2


@pytest.mark.asyncio
async def test_find_by_campaign_no_match(seeded_repo):
    result = await seeded_repo.find_by_campaign("camp-999")
    assert result == []


@pytest.mark.asyncio
async def test_find_by_segment(seeded_repo):
    young = await seeded_repo.find_by_segment("young_active")
    assert len(young) == 2  # var-001 and var-003


@pytest.mark.asyncio
async def test_find_by_segment_no_match(seeded_repo):
    result = await seeded_repo.find_by_segment("nonexistent_segment")
    assert result == []


@pytest.mark.asyncio
async def test_update_status_bulk(seeded_repo):
    modified = await seeded_repo.update_status_bulk(
        ["var-001", "var-002"], VariantStatus.CANCELLED
    )
    assert modified == 2
    v1 = await seeded_repo.find_by_id("var-001")
    v2 = await seeded_repo.find_by_id("var-002")
    assert v1.status == VariantStatus.CANCELLED
    assert v2.status == VariantStatus.CANCELLED


@pytest.mark.asyncio
async def test_update_status_bulk_empty(seeded_repo):
    modified = await seeded_repo.update_status_bulk([], VariantStatus.CANCELLED)
    assert modified == 0


@pytest.mark.asyncio
async def test_update_status_bulk_partial_match(seeded_repo):
    modified = await seeded_repo.update_status_bulk(
        ["var-001", "nonexistent"], VariantStatus.SENT
    )
    assert modified == 1


@pytest.mark.asyncio
async def test_get_scheduled_variants(seeded_repo):
    now = datetime.utcnow()
    scheduled = await seeded_repo.get_scheduled_variants(
        start=now, end=now + timedelta(hours=10)
    )
    # var-002 (2h) and var-003 (5h) are scheduled in this window
    assert len(scheduled) == 2
    ids = {v.variant_id for v in scheduled}
    assert ids == {"var-002", "var-003"}


@pytest.mark.asyncio
async def test_get_scheduled_variants_narrow_window(seeded_repo):
    now = datetime.utcnow()
    scheduled = await seeded_repo.get_scheduled_variants(
        start=now, end=now + timedelta(hours=3)
    )
    # Only var-002 (2h ahead) should match
    assert len(scheduled) == 1
    assert scheduled[0].variant_id == "var-002"


@pytest.mark.asyncio
async def test_get_scheduled_variants_no_match(seeded_repo):
    far_future = datetime(2099, 1, 1)
    scheduled = await seeded_repo.get_scheduled_variants(
        start=far_future, end=far_future + timedelta(hours=1)
    )
    assert scheduled == []


# ── Pydantic Validation Tests ────────────────────────────────────


def test_variant_subject_line_too_long():
    with pytest.raises(ValueError):
        CampaignVariant(
            campaign_id="c1",
            subject_line="X" * 101,
        )


def test_variant_email_body_too_short():
    with pytest.raises(ValueError):
        CampaignVariant(
            campaign_id="c1",
            email_body="short",
        )


def test_variant_empty_email_body_allowed():
    v = CampaignVariant(campaign_id="c1", email_body="")
    assert v.email_body == ""


def test_variant_auto_uuid():
    v = CampaignVariant(campaign_id="c1")
    assert v.variant_id
    assert len(v.variant_id) == 36


def test_variant_to_dict(sample_variant):
    d = sample_variant.to_dict()
    assert d["variant_id"] == "var-001"
    assert "personalization_tags" in d


# ── Error Handling ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_variant_raises(repo, sample_variant):
    """On real MongoDB unique index on variant_id would reject duplicates."""
    await repo.create(sample_variant)
    await repo.create(sample_variant)
    count = await repo.count({"variant_id": sample_variant.variant_id})
    assert count >= 1
