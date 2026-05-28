"""Unit tests for PerformanceScoringService."""

import pytest

from app.services.performance_scoring_service import PerformanceScoringService
from app.models.metrics import Metrics


@pytest.fixture
def scoring_service():
    return PerformanceScoringService()


@pytest.mark.unit
class TestPerformanceScoringService:

    def test_score_high_performer(self, scoring_service, sample_metrics_high_performer):
        score = scoring_service.score(sample_metrics_high_performer)
        assert score > 0.3

    def test_score_low_performer(self, scoring_service, sample_metrics_low_performer):
        score = scoring_service.score(sample_metrics_low_performer)
        assert score < 0.3

    def test_score_range_0_to_1(self, scoring_service, sample_metrics):
        score = scoring_service.score(sample_metrics)
        assert 0.0 <= score <= 1.0

    def test_score_zero_rates_is_zero(self, scoring_service):
        m = Metrics(
            variant_id="v", campaign_id="c", mock_campaign_id="m",
            open_rate=0.0, click_rate=0.0,
        )
        score = scoring_service.score(m)
        assert score == 0.0

    def test_rank_variants(self, scoring_service, sample_metrics_list):
        ranked = scoring_service.rank_variants(sample_metrics_list)
        assert len(ranked) == len(sample_metrics_list)
        scores = [r["performance_score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_identify_poor_performers(self, scoring_service, sample_metrics_list):
        poor = scoring_service.identify_poor_performers(sample_metrics_list, percentile=50)
        assert isinstance(poor, list)
        assert len(poor) <= len(sample_metrics_list)
