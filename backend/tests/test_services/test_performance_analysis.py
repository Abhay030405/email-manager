"""Tests for PerformanceAnalysisService."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.performance_analysis_service import PerformanceAnalysisService
from tests.test_services.conftest import make_metrics


def _make_service(metrics=None, campaigns=None, agg=None):
    metrics_repo = MagicMock()
    metrics_repo.find_by_campaign = AsyncMock(return_value=metrics or [])
    metrics_repo.get_metrics_history = AsyncMock(return_value=metrics or [])
    metrics_repo.calculate_trend = AsyncMock(return_value="stable")
    metrics_repo.calculate_campaign_aggregates = AsyncMock(
        return_value=agg or {"avg_open_rate": 0.0, "avg_click_rate": 0.0}
    )

    analytics_repo = MagicMock()
    analytics_repo.create_snapshot = AsyncMock()

    aggregation_repo = MagicMock()

    campaign_repo = MagicMock()
    campaign_repo.find_all = AsyncMock(return_value=campaigns or [])

    svc = PerformanceAnalysisService(
        metrics_repo=metrics_repo,
        analytics_repo=analytics_repo,
        aggregation_repo=aggregation_repo,
        campaign_repo=campaign_repo,
    )
    return svc, metrics_repo, analytics_repo, campaign_repo


# ── analyze_campaign_performance ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_campaign_performance_no_metrics():
    svc, *_ = _make_service(metrics=[])
    result = await svc.analyze_campaign_performance("camp-001")
    assert result["overall_metrics"] == {}
    assert "No metrics data available yet" in result["recommendations"][0]


@pytest.mark.asyncio
async def test_analyze_campaign_performance_with_data():
    m1 = make_metrics(variant_id="v1", total_sent=1000, unique_opens=400, unique_clicks=80,
                      open_rate=0.40, click_rate=0.08)
    m2 = make_metrics(variant_id="v2", total_sent=1000, unique_opens=300, unique_clicks=50,
                      open_rate=0.30, click_rate=0.05)
    svc, _, analytics_repo, _ = _make_service(metrics=[m1, m2])

    result = await svc.analyze_campaign_performance("camp-001")

    assert result["campaign_id"] == "camp-001"
    assert result["overall_metrics"]["total_sent"] == 2000
    assert result["overall_metrics"]["total_opens"] == 700
    assert result["overall_metrics"]["total_clicks"] == 130
    assert "variant_analysis" in result
    assert len(result["variant_analysis"]) == 2
    analytics_repo.create_snapshot.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_campaign_performance_variant_ranking():
    low = make_metrics(variant_id="low-var", open_rate=0.10, click_rate=0.02,
                       total_sent=500, unique_opens=50, unique_clicks=10)
    high = make_metrics(variant_id="high-var", open_rate=0.45, click_rate=0.10,
                        total_sent=500, unique_opens=225, unique_clicks=50)
    svc, *_ = _make_service(metrics=[low, high])

    result = await svc.analyze_campaign_performance("camp-001")
    ranked = result["variant_analysis"]
    assert ranked[0]["variant_id"] == "high-var"
    assert ranked[-1]["variant_id"] == "low-var"


@pytest.mark.asyncio
async def test_analyze_campaign_performance_recommendations_low_open():
    m = make_metrics(open_rate=0.10, click_rate=0.02, total_sent=1000, unique_opens=100, unique_clicks=20)
    svc, *_ = _make_service(metrics=[m])
    result = await svc.analyze_campaign_performance("camp-001")
    recs_text = " ".join(result["recommendations"])
    assert "Open rate" in recs_text or "open" in recs_text.lower()


@pytest.mark.asyncio
async def test_analyze_campaign_performance_snapshot_failure_does_not_raise():
    m = make_metrics()
    svc, _, analytics_repo, _ = _make_service(metrics=[m])
    analytics_repo.create_snapshot = AsyncMock(side_effect=Exception("db error"))
    result = await svc.analyze_campaign_performance("camp-001")
    assert result["campaign_id"] == "camp-001"


# ── calculate_trend ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calculate_trend_returns_dict():
    m = make_metrics(open_rate=0.30)
    svc, metrics_repo, *_ = _make_service(metrics=[m])
    metrics_repo.calculate_trend = AsyncMock(return_value="improving")
    metrics_repo.get_metrics_history = AsyncMock(return_value=[m, m])

    result = await svc.calculate_trend("camp-001", "open_rate", lookback_hours=24)
    assert "trend" in result
    assert "data_points" in result
    assert "confidence" in result


@pytest.mark.asyncio
async def test_calculate_trend_no_history():
    svc, metrics_repo, *_ = _make_service(metrics=[])
    metrics_repo.get_metrics_history = AsyncMock(return_value=[])

    result = await svc.calculate_trend("camp-001", "open_rate")
    assert result["data_points"] == 0
    assert result["projected_value"] == 0.0


# ── predict_final_metrics ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predict_final_metrics_no_history():
    svc, metrics_repo, *_ = _make_service(metrics=[])
    metrics_repo.get_metrics_history = AsyncMock(return_value=[])

    result = await svc.predict_final_metrics("camp-001")
    assert result["projected_open_rate"] == 0.0
    assert result["estimate_reliability"] == 0.0


@pytest.mark.asyncio
async def test_predict_final_metrics_with_history():
    metrics_list = [
        make_metrics(open_rate=0.30, click_rate=0.06),
        make_metrics(open_rate=0.32, click_rate=0.07),
        make_metrics(open_rate=0.34, click_rate=0.08),
    ]
    svc, metrics_repo, *_ = _make_service(metrics=metrics_list)
    metrics_repo.get_metrics_history = AsyncMock(return_value=metrics_list)

    result = await svc.predict_final_metrics("camp-001", based_on_hours=24)
    assert result["projected_open_rate"] >= 0.0
    assert result["projected_open_rate"] <= 100.0
    assert result["estimate_reliability"] > 0.0


@pytest.mark.asyncio
async def test_predict_final_metrics_reliability_capped_at_one():
    metrics_list = [make_metrics(open_rate=0.35) for _ in range(10)]
    svc, metrics_repo, *_ = _make_service(metrics=metrics_list)
    metrics_repo.get_metrics_history = AsyncMock(return_value=metrics_list)

    result = await svc.predict_final_metrics("camp-001")
    assert result["estimate_reliability"] <= 1.0


# ── compare_to_baseline ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compare_to_baseline_no_baseline():
    svc, metrics_repo, _, campaign_repo = _make_service(campaigns=[])
    metrics_repo.calculate_campaign_aggregates = AsyncMock(
        return_value={"avg_open_rate": 0.35, "avg_click_rate": 0.08}
    )

    result = await svc.compare_to_baseline("camp-001")
    assert result["status"] == "no_baseline"
    assert result["current_open_rate"] == pytest.approx(35.0, abs=0.1)


@pytest.mark.asyncio
async def test_compare_to_baseline_above_average():
    c_other = MagicMock()
    c_other.campaign_id = "camp-other"

    svc, metrics_repo, _, campaign_repo = _make_service(campaigns=[c_other])

    async def fake_agg(campaign_id):
        if campaign_id == "camp-001":
            return {"avg_open_rate": 0.45, "avg_click_rate": 0.10}
        return {"avg_open_rate": 0.30, "avg_click_rate": 0.07}

    metrics_repo.calculate_campaign_aggregates = AsyncMock(side_effect=fake_agg)

    result = await svc.compare_to_baseline("camp-001")
    assert result["status"] == "above_average"
    assert result["variance_percentage"] > 0


@pytest.mark.asyncio
async def test_compare_to_baseline_below_average():
    c_other = MagicMock()
    c_other.campaign_id = "camp-other"

    svc, metrics_repo, _, campaign_repo = _make_service(campaigns=[c_other])

    async def fake_agg(campaign_id):
        if campaign_id == "camp-001":
            return {"avg_open_rate": 0.15, "avg_click_rate": 0.03}
        return {"avg_open_rate": 0.35, "avg_click_rate": 0.08}

    metrics_repo.calculate_campaign_aggregates = AsyncMock(side_effect=fake_agg)

    result = await svc.compare_to_baseline("camp-001")
    assert result["status"] == "below_average"
    assert result["variance_percentage"] < 0
