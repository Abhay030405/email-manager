"""Tests for PerformanceScoringService."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.performance_scoring_service import PerformanceScoringService
from tests.test_services.conftest import make_metrics


def _make_service(metrics=None, variants=None):
    metrics_repo = MagicMock()
    metrics_repo.find_by_campaign = AsyncMock(return_value=metrics or [])

    variant_repo = MagicMock()
    variant_repo.find_by_campaign = AsyncMock(return_value=variants or [])

    return PerformanceScoringService(metrics_repo=metrics_repo, variant_repo=variant_repo)


def _make_variant(variant_id="v1", segment_name="premium"):
    v = MagicMock()
    v.variant_id = variant_id
    v.segment_name = segment_name
    return v


# ── calculate_performance_score ───────────────────────────────────────────────

def test_calculate_performance_score_formula():
    svc = _make_service()
    score = svc.calculate_performance_score(open_rate=30.0, click_rate=10.0)
    # 0.7 * (10/100) + 0.3 * (30/100) = 0.07 + 0.09 = 0.16
    assert score == pytest.approx(0.16, abs=0.001)


def test_calculate_performance_score_zeros():
    svc = _make_service()
    assert svc.calculate_performance_score(0.0, 0.0) == 0.0


def test_calculate_performance_score_maxed():
    svc = _make_service()
    score = svc.calculate_performance_score(100.0, 100.0)
    assert score == pytest.approx(1.0, abs=0.001)


def test_calculate_performance_score_click_weighted_more():
    svc = _make_service()
    high_click = svc.calculate_performance_score(open_rate=10.0, click_rate=50.0)
    high_open = svc.calculate_performance_score(open_rate=50.0, click_rate=10.0)
    assert high_click > high_open


def test_calculate_performance_score_clamped():
    svc = _make_service()
    # Inputs > 100 should be clamped to 1.0
    score = svc.calculate_performance_score(open_rate=200.0, click_rate=150.0)
    assert score <= 1.0


# ── compare_scores ────────────────────────────────────────────────────────────

def test_compare_scores_improvement():
    svc = _make_service()
    result = svc.compare_scores(0.20, 0.30)
    assert result["is_improvement"] is True
    assert result["percentage_change"] == pytest.approx(50.0, abs=0.1)


def test_compare_scores_decline():
    svc = _make_service()
    result = svc.compare_scores(0.30, 0.20)
    assert result["is_improvement"] is False
    assert result["percentage_change"] < 0


def test_compare_scores_significance_levels():
    svc = _make_service()
    assert svc.compare_scores(0.10, 0.20)["significance"] == "significant"
    assert svc.compare_scores(0.10, 0.105)["significance"] == "moderate"
    assert svc.compare_scores(0.10, 0.101)["significance"] == "minimal"


def test_compare_scores_zero_baseline():
    svc = _make_service()
    result = svc.compare_scores(0.0, 0.15)
    assert result["percentage_change"] == 100.0


# ── score_content_quality ─────────────────────────────────────────────────────

def test_score_content_quality_ideal_subject():
    svc = _make_service()
    result = svc.score_content_quality(
        subject="Exclusive deal: save 30% this week only!",
        body=" ".join(["word"] * 150),
    )
    assert result["subject_score"] >= 0.6
    assert result["overall_score"] > 0


def test_score_content_quality_short_subject_penalized():
    svc = _make_service()
    result = svc.score_content_quality(subject="Hi", body=" ".join(["word"] * 150))
    assert result["subject_score"] < 0.6


def test_score_content_quality_optimal_timing():
    svc = _make_service()
    # Wednesday 9 AM
    send_time = datetime(2025, 1, 8, 9, 0)  # Wednesday
    result = svc.score_content_quality("Test subject line that is 40-60 chars long!", "body " * 30, send_time)
    assert result["timing_score"] == 1.0


def test_score_content_quality_poor_timing():
    svc = _make_service()
    # Sunday midnight
    send_time = datetime(2025, 1, 5, 0, 0)  # Sunday
    result = svc.score_content_quality("Test subject", "body " * 30, send_time)
    assert result["timing_score"] < 0.5


def test_score_content_quality_has_opportunities():
    svc = _make_service()
    result = svc.score_content_quality(subject="Hi", body="short")
    assert len(result["improvement_opportunities"]) > 0


def test_score_content_quality_cta_boosts_body_score():
    svc = _make_service()
    without_cta = svc.score_content_quality("Subject line 40-60 chars exactly here!", "word " * 120)
    with_cta = svc.score_content_quality("Subject line 40-60 chars exactly here!", "word " * 120 + " click here")
    assert with_cta["body_score"] >= without_cta["body_score"]


# ── identify_poor_performers ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_identify_poor_performers_empty():
    svc = _make_service(metrics=[])
    result = await svc.identify_poor_performers("camp-001")
    assert result == []


@pytest.mark.asyncio
async def test_identify_poor_performers_single_variant():
    m = make_metrics(variant_id="v1")
    svc = _make_service(metrics=[m])
    result = await svc.identify_poor_performers("camp-001")
    assert result == []  # needs at least 2


@pytest.mark.asyncio
async def test_identify_poor_performers_bottom_25_percent():
    high = make_metrics(variant_id="v1", open_rate=0.45, click_rate=0.12)
    low = make_metrics(variant_id="v2", open_rate=0.10, click_rate=0.02)
    avg = make_metrics(variant_id="v3", open_rate=0.30, click_rate=0.07)
    avg2 = make_metrics(variant_id="v4", open_rate=0.28, click_rate=0.06)
    svc = _make_service(metrics=[high, low, avg, avg2], variants=[_make_variant("v1"), _make_variant("v2"), _make_variant("v3"), _make_variant("v4")])
    result = await svc.identify_poor_performers("camp-001", percentile=25)
    assert len(result) >= 1
    ids = [r["variant_id"] for r in result]
    assert "v2" in ids  # lowest performer


@pytest.mark.asyncio
async def test_identify_poor_performers_has_comparison_to_avg():
    m1 = make_metrics(variant_id="v1", open_rate=0.40, click_rate=0.10)
    m2 = make_metrics(variant_id="v2", open_rate=0.10, click_rate=0.02)
    svc = _make_service(metrics=[m1, m2], variants=[_make_variant("v1"), _make_variant("v2")])
    result = await svc.identify_poor_performers("camp-001", percentile=50)
    assert all("comparison_to_avg" in r for r in result)


# ── analyze_segment_performance ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_segment_performance_empty():
    svc = _make_service(metrics=[], variants=[])
    result = await svc.analyze_segment_performance("camp-001")
    assert result["best_segment"] is None
    assert result["worst_segment"] is None


@pytest.mark.asyncio
async def test_analyze_segment_performance_ranks_segments():
    v_prem = _make_variant("v1", "premium")
    v_std = _make_variant("v2", "standard")
    m_prem = make_metrics(variant_id="v1", open_rate=0.45, click_rate=0.12)
    m_std = make_metrics(variant_id="v2", open_rate=0.15, click_rate=0.03)
    svc = _make_service(metrics=[m_prem, m_std], variants=[v_prem, v_std])
    result = await svc.analyze_segment_performance("camp-001")
    assert result["best_segment"] == "premium"
    assert result["worst_segment"] == "standard"
