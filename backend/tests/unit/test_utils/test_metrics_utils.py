"""Unit tests for metrics_utils module."""

import pytest

from app.utils.metrics_utils import calculate_metrics


@pytest.mark.unit
class TestMetricsUtils:

    def test_calculate_performance_score(self):
        result = calculate_metrics(open_rate=0.40, click_rate=0.10)
        assert "performance_score" in result
        expected = round(0.7 * 0.10 + 0.3 * 0.40, 4)
        assert abs(result["performance_score"] - expected) < 0.01

    def test_performance_score_zero_rates(self):
        result = calculate_metrics(open_rate=0.0, click_rate=0.0)
        assert result["performance_score"] == 0.0

    def test_performance_score_max_rates(self):
        result = calculate_metrics(open_rate=1.0, click_rate=1.0)
        assert result["performance_score"] <= 1.0

    def test_calculate_metrics_returns_dict(self):
        result = calculate_metrics(open_rate=0.35, click_rate=0.08)
        assert isinstance(result, dict)

    def test_percentage_conversion(self):
        result = calculate_metrics(open_rate=0.35, click_rate=0.08)
        if "open_rate_pct" in result:
            assert result["open_rate_pct"] == 35.0
        if "click_rate_pct" in result:
            assert result["click_rate_pct"] == 8.0
