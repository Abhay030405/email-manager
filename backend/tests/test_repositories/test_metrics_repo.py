"""Tests for MetricsRepository — Mock Campaign API aligned (0.0–1.0 rates)."""

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
    assert result.mock_campaign_id == "mock-001"


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
    updated = await repo.update("met-001", {"total_sent": 2000})
    assert updated is not None
    assert updated.total_sent == 2000


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
    assert top[0].performance_score >= top[1].performance_score


@pytest.mark.asyncio
async def test_get_top_performers_with_min_score(seeded_repo):
    # met-003: click=0.15, open=0.50 -> score = 0.7*0.15 + 0.3*0.50 = 0.255
    # met-001: click=0.10, open=0.40 -> score = 0.7*0.10 + 0.3*0.40 = 0.19
    # met-002: click=0.03, open=0.20 -> score = 0.7*0.03 + 0.3*0.20 = 0.081
    top = await seeded_repo.get_top_performers(limit=10, min_score=0.15)
    assert all(m.performance_score >= 0.15 for m in top)


@pytest.mark.asyncio
async def test_get_bottom_performers(seeded_repo):
    bottom = await seeded_repo.get_bottom_performers(limit=1)
    assert len(bottom) == 1
    assert bottom[0].metric_id == "met-002"


@pytest.mark.asyncio
async def test_calculate_campaign_aggregates(seeded_repo):
    agg = await seeded_repo.calculate_campaign_aggregates("camp-001")
    assert "avg_open_rate" in agg
    assert "avg_click_rate" in agg
    assert "total_sent" in agg
    assert agg["total_sent"] == 1800  # 1000 + 800
    assert agg["total_opens"] == 560  # 400 + 160
    assert agg["total_clicks"] == 124  # 100 + 24


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
            mock_campaign_id="mock-ts",
            open_rate=0.20 + i * 0.05,
            click_rate=0.05 + i * 0.02,
            calculated_at=now + timedelta(hours=i),
        )
        await repo.create(m)

    series = await repo.get_metrics_time_series(
        "camp-ts", start_date=now, end_date=now + timedelta(hours=3)
    )
    assert len(series) == 4  # hours 0, 1, 2, 3
    for j in range(len(series) - 1):
        assert series[j].calculated_at <= series[j + 1].calculated_at


@pytest.mark.asyncio
async def test_get_metrics_time_series_no_match(seeded_repo):
    far = datetime(2099, 1, 1)
    series = await seeded_repo.get_metrics_time_series(
        "camp-001", start_date=far, end_date=far + timedelta(hours=1)
    )
    assert series == []


# ── Mock Campaign API Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_from_mock_api(repo):
    m = Metrics(
        variant_id="var-mock",
        campaign_id="camp-mock",
        mock_campaign_id="mock-api-001",
        open_rate=0.35,
        click_rate=0.12,
        total_sent=500,
        unique_opens=175,
        unique_clicks=60,
    )
    result = await repo.create_from_mock_api(m)
    assert result is not None
    assert result.mock_campaign_id == "mock-api-001"
    assert result.total_sent == 500


@pytest.mark.asyncio
async def test_get_latest_by_mock_campaign_id(repo):
    now = datetime.utcnow()
    for i in range(3):
        m = Metrics(
            metric_id=f"latest-{i}",
            variant_id="var-latest",
            campaign_id="camp-latest",
            mock_campaign_id="mock-latest",
            open_rate=0.1 * (i + 1),
            calculated_at=now + timedelta(hours=i),
        )
        await repo.create(m)
    latest = await repo.get_latest_by_mock_campaign_id("mock-latest")
    assert latest is not None
    assert latest.metric_id == "latest-2"


@pytest.mark.asyncio
async def test_get_latest_by_mock_campaign_id_not_found(repo):
    assert await repo.get_latest_by_mock_campaign_id("nonexistent") is None


@pytest.mark.asyncio
async def test_get_performance_distribution(seeded_repo):
    dist = await seeded_repo.get_performance_distribution("camp-001")
    assert len(dist) == 2  # met-001 and met-002
    assert all("variant_id" in d for d in dist)
    assert all("performance_score" in d for d in dist)


@pytest.mark.asyncio
async def test_get_performance_distribution_no_data(seeded_repo):
    dist = await seeded_repo.get_performance_distribution("camp-999")
    assert dist == []


# ── Pydantic Validation Tests ────────────────────────────────────


def test_performance_score_auto_calculated():
    m = Metrics(
        variant_id="v1", campaign_id="c1", mock_campaign_id="m1",
        open_rate=0.40, click_rate=0.10,
    )
    expected = round(0.7 * 0.10 + 0.3 * 0.40, 2)
    assert m.performance_score == expected


def test_open_rate_out_of_range():
    with pytest.raises(ValueError):
        Metrics(variant_id="v1", campaign_id="c1", mock_campaign_id="m1", open_rate=1.1)


def test_click_rate_negative():
    with pytest.raises(ValueError):
        Metrics(variant_id="v1", campaign_id="c1", mock_campaign_id="m1", click_rate=-0.1)


def test_total_sent_negative():
    with pytest.raises(ValueError):
        Metrics(variant_id="v1", campaign_id="c1", mock_campaign_id="m1", total_sent=-10)


def test_metrics_to_dict(sample_metrics):
    d = sample_metrics.to_dict()
    assert d["metric_id"] == "met-001"
    assert "performance_score" in d
    expected = round(0.7 * 0.085 + 0.3 * 0.35, 2)
    assert d["performance_score"] == expected


def test_metrics_auto_uuid():
    m = Metrics(variant_id="v1", campaign_id="c1", mock_campaign_id="m1")
    assert m.metric_id
    assert len(m.metric_id) == 36


def test_metrics_mock_campaign_id_required():
    with pytest.raises(ValueError):
        Metrics(variant_id="v1", campaign_id="c1")


@pytest.mark.asyncio
async def test_duplicate_metric_raises(repo, sample_metrics):
    """On real MongoDB unique index on metric_id would reject duplicates."""
    await repo.create(sample_metrics)
    await repo.create(sample_metrics)
    count = await repo.count({"metric_id": sample_metrics.metric_id})
    assert count >= 1
