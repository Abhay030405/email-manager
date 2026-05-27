"""Tests for MetricsAggregationService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.metrics_aggregation_service import MetricsAggregationService
from tests.test_services.conftest import make_metrics


def _make_service(metrics=None, variants=None):
    metrics_repo = MagicMock()
    metrics_repo.find_by_campaign = AsyncMock(return_value=metrics or [])
    metrics_repo.get_metrics_time_series = AsyncMock(return_value=metrics or [])

    aggregation_repo = MagicMock()

    async def fake_upsert(campaign_id, agg_type, agg_key, data):
        from app.models.metric_aggregation import MetricAggregation
        return MetricAggregation(**data)

    aggregation_repo.upsert_for_campaign = AsyncMock(side_effect=fake_upsert)

    variant_repo = MagicMock()
    variant_repo.find_by_campaign = AsyncMock(return_value=variants or [])

    svc = MetricsAggregationService(
        metrics_repo=metrics_repo,
        aggregation_repo=aggregation_repo,
        variant_repo=variant_repo,
        campaign_repo=MagicMock(),
    )
    return svc, metrics_repo, aggregation_repo, variant_repo


# ── aggregate_campaign_metrics ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aggregate_campaign_metrics_with_data():
    m1 = make_metrics(variant_id="v1", total_sent=1000, unique_opens=300, unique_clicks=60,
                      open_rate=0.30, click_rate=0.06)
    m2 = make_metrics(variant_id="v2", total_sent=1000, unique_opens=400, unique_clicks=90,
                      open_rate=0.40, click_rate=0.09)
    svc, *_ = _make_service(metrics=[m1, m2])

    result = await svc.aggregate_campaign_metrics("camp-001")
    assert result.total_sent == 2000
    assert result.total_opens == 700
    assert result.total_clicks == 150
    assert result.aggregation_type == "campaign_total"


@pytest.mark.asyncio
async def test_aggregate_campaign_metrics_empty():
    svc, *_ = _make_service(metrics=[])

    result = await svc.aggregate_campaign_metrics("camp-001")
    assert result.data_point_count == 0
    assert result.total_sent == 0


@pytest.mark.asyncio
async def test_aggregate_campaign_metrics_rates_are_percentages():
    m = make_metrics(total_sent=1000, unique_opens=350, unique_clicks=80,
                     open_rate=0.35, click_rate=0.08)
    svc, *_ = _make_service(metrics=[m])

    result = await svc.aggregate_campaign_metrics("camp-001")
    assert result.open_rate == pytest.approx(35.0, abs=0.1)
    assert result.click_rate == pytest.approx(8.0, abs=0.1)


# ── aggregate_segment_metrics ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aggregate_segment_metrics_filters_by_segment():
    v1 = MagicMock()
    v1.variant_id = "var-seg1"
    v1.segment_name = "premium"
    v2 = MagicMock()
    v2.variant_id = "var-seg2"
    v2.segment_name = "standard"

    m1 = make_metrics(variant_id="var-seg1", total_sent=500, unique_opens=200, unique_clicks=40)
    m2 = make_metrics(variant_id="var-seg2", total_sent=500, unique_opens=100, unique_clicks=20)
    svc, *_ = _make_service(metrics=[m1, m2], variants=[v1, v2])

    result = await svc.aggregate_segment_metrics("camp-001", "premium")
    assert result.aggregation_key == "premium"
    assert result.aggregation_type == "segment"
    assert result.total_sent == 500


@pytest.mark.asyncio
async def test_aggregate_segment_metrics_no_matching_variants():
    v1 = MagicMock()
    v1.variant_id = "var-seg1"
    v1.segment_name = "other"
    m1 = make_metrics(variant_id="var-seg1")
    svc, *_ = _make_service(metrics=[m1], variants=[v1])

    result = await svc.aggregate_segment_metrics("camp-001", "premium")
    assert result.data_point_count == 0


# ── aggregate_variant_metrics ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aggregate_variant_metrics_filters_correctly():
    m1 = make_metrics(variant_id="target-var", total_sent=800, unique_opens=280, unique_clicks=56)
    m2 = make_metrics(variant_id="other-var")
    svc, *_ = _make_service(metrics=[m1, m2])

    result = await svc.aggregate_variant_metrics("camp-001", "target-var")
    assert result.aggregation_key == "target-var"
    assert result.aggregation_type == "variant"
    assert result.total_sent == 800


# ── compare_variants ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compare_variants_ranks_by_performance_score():
    low = make_metrics(variant_id="low", open_rate=0.10, click_rate=0.02)
    high = make_metrics(variant_id="high", open_rate=0.40, click_rate=0.10)
    svc, *_ = _make_service(metrics=[low, high])

    result = await svc.compare_variants("camp-001")
    assert result["best_variant"]["variant_id"] == "high"
    assert result["worst_variant"]["variant_id"] == "low"


@pytest.mark.asyncio
async def test_compare_variants_no_data():
    svc, *_ = _make_service(metrics=[])
    result = await svc.compare_variants("camp-001")
    assert result["best_variant"] is None
    assert result["worst_variant"] is None


@pytest.mark.asyncio
async def test_compare_variants_single():
    m = make_metrics(variant_id="only")
    svc, *_ = _make_service(metrics=[m])
    result = await svc.compare_variants("camp-001")
    assert result["best_variant"]["variant_id"] == "only"
    assert result["worst_variant"]["variant_id"] == "only"


@pytest.mark.asyncio
async def test_compare_variants_all_variants_present():
    m1 = make_metrics(variant_id="v1", open_rate=0.35, click_rate=0.08)
    m2 = make_metrics(variant_id="v2", open_rate=0.20, click_rate=0.04)
    m3 = make_metrics(variant_id="v3", open_rate=0.45, click_rate=0.12)
    svc, *_ = _make_service(metrics=[m1, m2, m3])

    result = await svc.compare_variants("camp-001")
    assert len(result["all_variants"]) == 3
    assert result["variance"] >= 0.0


# ── compare_segments ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compare_segments_ranks_by_open_rate():
    v1 = MagicMock()
    v1.variant_id = "v1"
    v1.segment_name = "premium"
    v2 = MagicMock()
    v2.variant_id = "v2"
    v2.segment_name = "standard"

    m1 = make_metrics(variant_id="v1", open_rate=0.45)
    m2 = make_metrics(variant_id="v2", open_rate=0.20)
    svc, *_ = _make_service(metrics=[m1, m2], variants=[v1, v2])

    result = await svc.compare_segments("camp-001")
    assert result["best_segment"]["segment_name"] == "premium"
    assert result["worst_segment"]["segment_name"] == "standard"


@pytest.mark.asyncio
async def test_compare_segments_no_data():
    svc, *_ = _make_service(metrics=[], variants=[])
    result = await svc.compare_segments("camp-001")
    assert result["best_segment"] is None
    assert result["segments"] == []
