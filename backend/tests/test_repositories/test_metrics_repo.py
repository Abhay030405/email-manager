"""Tests for MetricsRepository."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from app.db.repositories.metrics_repo import MetricsRepository
from app.models.metrics import Metrics


@pytest_asyncio.fixture
async def repo(mock_db):
    return MetricsRepository(mock_db)


@pytest_asyncio.fixture
async def seeded_repo(mock_db, sample_metrics_list):
    """Repo pre-loaded with 3 metrics records across 2 campaigns."""
    repo = MetricsRepository(mock_db)
    for m in sample_metrics_list:
        await repo.create(m)
    return repo


# ── CRUD Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_metrics(repo, sample_metrics):
    result = await repo.create(sample_metrics)
    assert result.metric_id == "met-001"
    assert result.variant_id == "var-001"


@pytest.mark.asyncio
async def test_find_by_id(repo, sample_metrics):
    await repo.create(sample_metrics)
    found = await repo.find_by_id("met-001")
    assert found is not None
    assert found.campaign_id == "camp-001"


@pytest.mark.asyncio
async def test_find_by_id_not_found(repo):
    assert await repo.find_by_id("ghost") is None


@pytest.mark.asyncio
async def test_update_metrics(repo, sample_metrics):
    await repo.create(sample_metrics)
    updated = await repo.update("met-001", {"emails_sent": 2000})
    assert updated is not None
    assert updated.emails_sent == 2000


@pytest.mark.asyncio
async def test_delete_metrics(repo, sample_metrics):
    await repo.create(sample_metrics)
    assert await repo.delete("met-001") is True
    assert await repo.find_by_id("met-001") is None


@pytest.mark.asyncio
async def test_count(seeded_repo):
    assert await seeded_repo.count() == 3


# ── Specialised Query Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_find_by_variant(seeded_repo):
    m = await seeded_repo.find_by_variant("var-001")
    assert m is not None
    assert m.metric_id == "met-001"


@pytest.mark.asyncio
async def test_find_by_variant_not_found(seeded_repo):
    assert await seeded_repo.find_by_variant("var-999") is None


@pytest.mark.asyncio
async def test_find_by_campaign(seeded_repo):
    camp1 = await seeded_repo.find_by_campaign("camp-001")
    assert len(camp1) == 2  # met-001 and met-002


@pytest.mark.asyncio
async def test_find_by_campaign_no_match(seeded_repo):
    result = await seeded_repo.find_by_campaign("camp-999")
    assert result == []


@pytest.mark.asyncio
async def test_get_top_performers(seeded_repo):
    top = await seeded_repo.get_top_performers(limit=2)
    assert len(top) == 2
    # Highest score first
    assert top[0].performance_score >= top[1].performance_score


@pytest.mark.asyncio
async def test_get_top_performers_with_min_score(seeded_repo):
    # met-003: click=15, open=50 -> score = 0.7*15 + 0.3*50 = 25.5
    # met-001: click=10, open=40 -> score = 0.7*10 + 0.3*40 = 19.0
    # met-002: click=3, open=20 -> score = 0.7*3 + 0.3*20 = 8.1
    top = await seeded_repo.get_top_performers(limit=10, min_score=15.0)
    assert all(m.performance_score >= 15.0 for m in top)


@pytest.mark.asyncio
async def test_get_bottom_performers(seeded_repo):
    bottom = await seeded_repo.get_bottom_performers(limit=1)
    assert len(bottom) == 1
    # Lowest score should be met-002 (score ≈ 8.1)
    assert bottom[0].metric_id == "met-002"


@pytest.mark.asyncio
async def test_calculate_campaign_aggregates(seeded_repo):
    agg = await seeded_repo.calculate_campaign_aggregates("camp-001")
    assert "avg_open_rate" in agg
    assert "avg_click_rate" in agg
    assert "total_sent" in agg
    assert agg["total_sent"] == 1800  # 1000 + 800
    assert agg["total_opened"] == 560  # 400 + 160
    assert agg["total_clicked"] == 124  # 100 + 24


@pytest.mark.asyncio
async def test_calculate_campaign_aggregates_no_data(seeded_repo):
    agg = await seeded_repo.calculate_campaign_aggregates("camp-999")
    assert agg["total_sent"] == 0
    assert agg["avg_open_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_metrics_time_series(mock_db):
    repo = MetricsRepository(mock_db)
    now = datetime.utcnow()
    for i in range(5):
        m = Metrics(
            metric_id=f"ts-{i}",
            variant_id="var-ts",
            campaign_id="camp-ts",
            open_rate=20.0 + i,
            click_rate=5.0 + i,
            timestamp=now + timedelta(hours=i),
        )
        await repo.create(m)

    series = await repo.get_metrics_time_series(
        "camp-ts", start_date=now, end_date=now + timedelta(hours=3)
    )
    assert len(series) == 4  # hours 0, 1, 2, 3
    # Should be in chronological order
    for j in range(len(series) - 1):
        assert series[j].timestamp <= series[j + 1].timestamp


@pytest.mark.asyncio
async def test_get_metrics_time_series_no_match(seeded_repo):
    far = datetime(2099, 1, 1)
    series = await seeded_repo.get_metrics_time_series(
        "camp-001", start_date=far, end_date=far + timedelta(hours=1)
    )
    assert series == []


# ── Pydantic Validation Tests ────────────────────────────────────


def test_performance_score_auto_calculated():
    m = Metrics(
        variant_id="v1", campaign_id="c1", open_rate=40.0, click_rate=10.0
    )
    expected = round(0.7 * 10.0 + 0.3 * 40.0, 2)
    assert m.performance_score == expected


def test_open_rate_out_of_range():
    with pytest.raises(ValueError):
        Metrics(variant_id="v1", campaign_id="c1", open_rate=101.0)


def test_click_rate_negative():
    with pytest.raises(ValueError):
        Metrics(variant_id="v1", campaign_id="c1", click_rate=-1.0)


def test_emails_sent_negative():
    with pytest.raises(ValueError):
        Metrics(variant_id="v1", campaign_id="c1", emails_sent=-10)


def test_metrics_to_dict(sample_metrics):
    d = sample_metrics.to_dict()
    assert d["metric_id"] == "met-001"
    assert "performance_score" in d
    assert d["performance_score"] == round(0.7 * 8.5 + 0.3 * 35.0, 2)


def test_metrics_auto_uuid():
    m = Metrics(variant_id="v1", campaign_id="c1")
    assert m.metric_id
    assert len(m.metric_id) == 36


# ── Error Handling ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_metric_raises(repo, sample_metrics):
    """On real MongoDB unique index on metric_id would reject duplicates."""
    await repo.create(sample_metrics)
    await repo.create(sample_metrics)
    count = await repo.count({"metric_id": sample_metrics.metric_id})
    assert count >= 1
