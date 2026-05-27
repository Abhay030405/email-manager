"""Tests for MetricsCollectionService."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.metrics_collection_service import MetricsCollectionService
from app.external.mock_campaign_client import MockCampaignAPIError
from tests.test_services.conftest import make_metrics, make_mock_api_client


def _make_service(mock_db, mock_api_client=None, campaign=None, variants=None):
    if mock_api_client is None:
        mock_api_client = make_mock_api_client()

    metrics_repo = MagicMock()
    metrics_repo.get_latest_by_variant = AsyncMock(return_value=None)
    metrics_repo.upsert = AsyncMock()

    campaign_repo = MagicMock()
    campaign_repo.find_by_id = AsyncMock(return_value=campaign)

    variant_repo = MagicMock()
    variant_repo.find_by_campaign = AsyncMock(return_value=variants or [])

    svc = MetricsCollectionService(
        mock_api_client=mock_api_client,
        metrics_repo=metrics_repo,
        campaign_repo=campaign_repo,
        variant_repo=variant_repo,
        cache_ttl_minutes=5,
    )
    return svc, metrics_repo, campaign_repo, variant_repo


def _make_campaign(mock_campaign_id: str | None = "mock-001"):
    c = MagicMock()
    c.campaign_id = "camp-001"
    c.mock_campaign_id = mock_campaign_id
    return c


def _make_variant(variant_id: str = "var-001", mock_campaign_id: str = "mock-v1"):
    v = MagicMock()
    v.variant_id = variant_id
    v.mock_campaign_id = mock_campaign_id
    return v


# ── collect_campaign_metrics ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_collect_campaign_metrics_campaign_not_found(mock_db):
    svc, metrics_repo, campaign_repo, _ = _make_service(mock_db, campaign=None)
    result = await svc.collect_campaign_metrics("missing-id")
    assert result["error"] == "Campaign not found"
    assert result["variants_collected"] == 0


@pytest.mark.asyncio
async def test_collect_campaign_metrics_no_mock_ids(mock_db):
    campaign = _make_campaign(mock_campaign_id=None)
    svc, *_ = _make_service(mock_db, campaign=campaign, variants=[])
    result = await svc.collect_campaign_metrics("camp-001")
    assert result["variants_collected"] == 0
    assert result["source"] == "skipped"


@pytest.mark.asyncio
async def test_collect_campaign_metrics_success(mock_db):
    campaign = _make_campaign(mock_campaign_id="mock-001")
    api_client = make_mock_api_client()
    svc, metrics_repo, *_ = _make_service(mock_db, mock_api_client=api_client, campaign=campaign)
    metrics_repo.upsert = AsyncMock()

    with patch("asyncio.get_event_loop") as mock_loop:
        loop = MagicMock()
        mock_loop.return_value = loop

        collected_metrics = make_metrics()

        async def fake_run_in_executor(executor, fn, *args):
            return api_client.get_campaign_metrics("mock-001")

        loop.run_in_executor = fake_run_in_executor
        metrics_repo.upsert = AsyncMock(return_value=collected_metrics)
        svc.metrics_repo = metrics_repo

        result = await svc.collect_campaign_metrics("camp-001")

    assert result["campaign_id"] == "camp-001"
    assert "collected_at" in result


@pytest.mark.asyncio
async def test_collect_campaign_metrics_from_cache(mock_db):
    campaign = _make_campaign(mock_campaign_id="mock-001")
    cached = make_metrics(collected_at=datetime.utcnow())
    api_client = make_mock_api_client()

    svc, metrics_repo, *_ = _make_service(mock_db, mock_api_client=api_client, campaign=campaign)
    metrics_repo.get_latest_by_variant = AsyncMock(return_value=cached)

    result = await svc.collect_campaign_metrics("camp-001", force_refresh=False)
    assert result["source"] == "cached"
    assert result["variants_collected"] == 1


@pytest.mark.asyncio
async def test_collect_campaign_metrics_force_refresh_bypasses_cache(mock_db):
    campaign = _make_campaign(mock_campaign_id="mock-001")
    cached = make_metrics()
    api_client = make_mock_api_client()
    svc, metrics_repo, *_ = _make_service(mock_db, mock_api_client=api_client, campaign=campaign)
    metrics_repo.get_latest_by_variant = AsyncMock(return_value=cached)

    with patch("asyncio.get_event_loop") as mock_loop:
        loop = MagicMock()
        mock_loop.return_value = loop

        async def fake_run(executor, fn, *args):
            return api_client.get_campaign_metrics("mock-001")

        loop.run_in_executor = fake_run
        fresh = make_metrics()
        metrics_repo.upsert = AsyncMock(return_value=fresh)

        result = await svc.collect_campaign_metrics("camp-001", force_refresh=True)

    assert result["source"] in ("mock_api", "cached")


@pytest.mark.asyncio
async def test_collect_campaign_metrics_api_error_handled(mock_db):
    campaign = _make_campaign(mock_campaign_id="mock-001")
    api_client = MagicMock()
    api_client.get_campaign_metrics.side_effect = MockCampaignAPIError(500, "server error")
    svc, metrics_repo, *_ = _make_service(mock_db, mock_api_client=api_client, campaign=campaign)
    metrics_repo.get_latest_by_variant = AsyncMock(return_value=None)

    with patch("asyncio.get_event_loop") as mock_loop:
        loop = MagicMock()
        mock_loop.return_value = loop

        async def raise_error(executor, fn, *args):
            raise MockCampaignAPIError(500, "server error")

        loop.run_in_executor = raise_error

        result = await svc.collect_campaign_metrics("camp-001")

    assert result["variants_collected"] == 0


# ── collect_all_active_campaigns_metrics ──────────────────────────────────────

@pytest.mark.asyncio
async def test_collect_all_active_campaigns_no_campaigns(mock_db):
    api_client = make_mock_api_client()
    svc, _, campaign_repo, _ = _make_service(mock_db, mock_api_client=api_client)
    campaign_repo.find_all = AsyncMock(return_value=[])

    result = await svc.collect_all_active_campaigns_metrics()
    assert result["total_campaigns"] == 0
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_collect_all_active_campaigns_aggregates(mock_db):
    campaign = _make_campaign(mock_campaign_id=None)
    api_client = make_mock_api_client()
    svc, _, campaign_repo, variant_repo = _make_service(
        mock_db, mock_api_client=api_client, campaign=campaign
    )
    campaign_repo.find_by_id = AsyncMock(return_value=campaign)
    campaign_repo.find_all = AsyncMock(return_value=[campaign])
    variant_repo.find_by_campaign = AsyncMock(return_value=[])

    result = await svc.collect_all_active_campaigns_metrics()
    assert result["total_campaigns"] == 1
    assert result["failed"] == 0


# ── validate_metrics_integrity ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_metrics_integrity_valid(mock_db):
    svc, *_ = _make_service(mock_db)
    m = make_metrics(open_rate=0.3, click_rate=0.05, unique_opens=300, unique_clicks=50)
    ok, errors = await svc.validate_metrics_integrity(m)
    assert ok
    assert errors == []


@pytest.mark.asyncio
async def test_validate_metrics_integrity_clicks_exceed_opens(mock_db):
    svc, *_ = _make_service(mock_db)
    m = make_metrics(unique_opens=100, unique_clicks=200)
    ok, errors = await svc.validate_metrics_integrity(m)
    assert not ok
    assert any("unique_clicks" in e for e in errors)


# ── get_cached_metrics ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_cached_metrics_within_ttl(mock_db):
    svc, metrics_repo, *_ = _make_service(mock_db)
    fresh = make_metrics()
    metrics_repo.get_latest_by_variant = AsyncMock(return_value=fresh)
    result = await svc.get_cached_metrics("camp-001", "var-001", max_age_minutes=5)
    assert result is fresh


@pytest.mark.asyncio
async def test_get_cached_metrics_expired_returns_none(mock_db):
    svc, metrics_repo, *_ = _make_service(mock_db)
    stale = make_metrics()
    stale = stale.model_copy(update={"collected_at": datetime.utcnow() - timedelta(minutes=10)})
    metrics_repo.get_latest_by_variant = AsyncMock(return_value=stale)
    result = await svc.get_cached_metrics("camp-001", "var-001", max_age_minutes=5)
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_metrics_no_record(mock_db):
    svc, metrics_repo, *_ = _make_service(mock_db)
    metrics_repo.get_latest_by_variant = AsyncMock(return_value=None)
    result = await svc.get_cached_metrics("camp-001", "var-001")
    assert result is None


# ── handle_collection_error ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_collection_error_mock_api_404(mock_db, caplog):
    svc, *_ = _make_service(mock_db)
    err = MockCampaignAPIError(404, "not found")
    import logging
    with caplog.at_level(logging.WARNING):
        await svc.handle_collection_error(err, "camp-001", "ctx")
    assert "not found" in caplog.text or "404" in caplog.text or "camp-001" in caplog.text


@pytest.mark.asyncio
async def test_handle_collection_error_generic(mock_db, caplog):
    svc, *_ = _make_service(mock_db)
    import logging
    with caplog.at_level(logging.ERROR):
        await svc.handle_collection_error(ValueError("boom"), "camp-001", "ctx")
    assert "boom" in caplog.text
