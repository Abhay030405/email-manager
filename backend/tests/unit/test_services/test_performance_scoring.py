"""Unit tests for PerformanceScoringService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.performance_scoring_service import PerformanceScoringService


def _make_svc():
    metrics_repo = MagicMock()
    metrics_repo.find_by_campaign = AsyncMock(return_value=[])
    variant_repo = MagicMock()
    variant_repo.find_by_campaign = AsyncMock(return_value=[])
    return PerformanceScoringService(metrics_repo=metrics_repo, variant_repo=variant_repo)


@pytest.mark.unit
class TestPerformanceScoringService:

    def test_score_high_performer(self):
        svc = _make_svc()
        score = svc.calculate_performance_score(open_rate=80.0, click_rate=40.0)
        assert score > 0.3

    def test_score_low_performer(self):
        svc = _make_svc()
        score = svc.calculate_performance_score(open_rate=5.0, click_rate=1.0)
        assert score < 0.3

    def test_score_range_0_to_1(self):
        svc = _make_svc()
        score = svc.calculate_performance_score(open_rate=35.0, click_rate=8.5)
        assert 0.0 <= score <= 1.0

    def test_score_zero_rates_is_zero(self):
        svc = _make_svc()
        score = svc.calculate_performance_score(open_rate=0.0, click_rate=0.0)
        assert score == 0.0

    def test_score_click_weighted_higher(self):
        svc = _make_svc()
        high_click = svc.calculate_performance_score(open_rate=10.0, click_rate=50.0)
        high_open = svc.calculate_performance_score(open_rate=50.0, click_rate=10.0)
        assert high_click > high_open

    def test_compare_scores_improvement(self):
        svc = _make_svc()
        result = svc.compare_scores(0.10, 0.20)
        assert result["is_improvement"] is True
        assert result["percentage_change"] > 0

    def test_compare_scores_decline(self):
        svc = _make_svc()
        result = svc.compare_scores(0.20, 0.10)
        assert result["is_improvement"] is False

    def test_compare_scores_significance_levels(self):
        svc = _make_svc()
        assert svc.compare_scores(0.10, 0.20)["significance"] == "significant"
        assert svc.compare_scores(0.10, 0.105)["significance"] == "moderate"
        assert svc.compare_scores(0.10, 0.101)["significance"] == "minimal"

    def test_score_content_quality_returns_dict(self):
        svc = _make_svc()
        result = svc.score_content_quality(
            subject="Exclusive deal: save 30% this week only!",
            body="word " * 150,
        )
        assert "overall_score" in result
        assert "subject_score" in result
        assert "body_score" in result

    def test_score_content_quality_short_subject_penalized(self):
        svc = _make_svc()
        result = svc.score_content_quality(subject="Hi", body="word " * 150)
        assert result["subject_score"] < 0.9
