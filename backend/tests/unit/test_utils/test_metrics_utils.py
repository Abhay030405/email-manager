"""Unit tests for metrics_utils module."""

import pytest

from app.utils.metrics_utils import (
    calculate_performance_score,
    convert_mock_api_metrics_to_percentages,
    calculate_engagement_score,
    calculate_std_dev,
    calculate_percentile,
    calculate_trend,
)


@pytest.mark.unit
class TestMetricsUtils:

    # ── calculate_performance_score (accepts 0-100 percentages) ──

    def test_performance_score_formula(self):
        # 0.7 * (8/100) + 0.3 * (40/100) = 0.056 + 0.12 = 0.176
        score = calculate_performance_score(open_rate=40.0, click_rate=8.0)
        expected = round(0.7 * (8.0 / 100) + 0.3 * (40.0 / 100), 4)
        assert abs(score - expected) < 0.001

    def test_performance_score_zero_rates(self):
        score = calculate_performance_score(open_rate=0.0, click_rate=0.0)
        assert score == pytest.approx(0.0, abs=1e-9)

    def test_performance_score_max_rates(self):
        score = calculate_performance_score(open_rate=100.0, click_rate=100.0)
        assert score <= 1.0

    def test_performance_score_click_weighted_more(self):
        high_click = calculate_performance_score(open_rate=10.0, click_rate=50.0)
        high_open = calculate_performance_score(open_rate=50.0, click_rate=10.0)
        assert high_click > high_open

    # ── convert_mock_api_metrics_to_percentages ───────────────────

    def test_converts_decimal_rates_to_percentages(self):
        raw = {"open_rate": 0.35, "click_rate": 0.08, "click_through_rate": 0.06}
        result = convert_mock_api_metrics_to_percentages(raw)
        assert result["open_rate"] == pytest.approx(35.0, abs=0.01)
        assert result["click_rate"] == pytest.approx(8.0, abs=0.01)

    def test_non_rate_fields_unchanged(self):
        raw = {"open_rate": 0.35, "total_sent": 1000}
        result = convert_mock_api_metrics_to_percentages(raw)
        assert result["total_sent"] == 1000

    def test_missing_rate_fields_safe(self):
        raw = {"total_sent": 500}
        result = convert_mock_api_metrics_to_percentages(raw)
        assert isinstance(result, dict)
        assert result["total_sent"] == 500

    # ── calculate_engagement_score (open, click, ctr — 0-100) ─────

    def test_engagement_score_returns_float(self):
        score = calculate_engagement_score(open_rate=35.0, click_rate=8.5, ctr=6.0)
        assert isinstance(score, float)

    def test_engagement_score_perfect(self):
        score = calculate_engagement_score(open_rate=100.0, click_rate=100.0, ctr=100.0)
        assert score == pytest.approx(100.0, abs=0.01)

    def test_engagement_score_zero(self):
        score = calculate_engagement_score(open_rate=0.0, click_rate=0.0, ctr=0.0)
        assert score == pytest.approx(0.0, abs=1e-9)

    # ── calculate_std_dev ─────────────────────────────────────────

    def test_std_dev_identical_values(self):
        result = calculate_std_dev([5.0, 5.0, 5.0])
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_std_dev_single_value_is_zero(self):
        result = calculate_std_dev([3.5])
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_std_dev_positive_for_varied_values(self):
        result = calculate_std_dev([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result > 0.0

    def test_std_dev_empty_returns_zero(self):
        result = calculate_std_dev([])
        assert result == pytest.approx(0.0, abs=1e-9)

    # ── calculate_percentile ──────────────────────────────────────

    def test_percentile_returns_int(self):
        pct = calculate_percentile(5.0, [1.0, 5.0, 10.0])
        assert isinstance(pct, int)

    def test_percentile_minimum_value_is_low(self):
        pct = calculate_percentile(1.0, [1.0, 5.0, 7.0, 10.0])
        assert pct <= 25

    def test_percentile_empty_list_returns_zero(self):
        pct = calculate_percentile(5.0, [])
        assert pct == 0

    def test_percentile_in_range_0_to_100(self):
        pct = calculate_percentile(3.0, [1.0, 2.0, 3.0, 4.0, 5.0])
        assert 0 <= pct <= 100

    # ── calculate_trend (returns tuple[str, float]) ───────────────

    def test_trend_improving_returns_improving(self):
        direction, rate = calculate_trend([0.10, 0.15, 0.20, 0.25])
        assert direction == "improving"
        assert rate > 0

    def test_trend_stable_returns_stable(self):
        direction, rate = calculate_trend([0.30, 0.30, 0.30, 0.30])
        assert direction == "stable"

    def test_trend_declining_returns_declining(self):
        direction, rate = calculate_trend([0.30, 0.25, 0.20, 0.15])
        assert direction == "declining"
        assert rate < 0

    def test_trend_empty_returns_stable(self):
        direction, rate = calculate_trend([])
        assert direction == "stable"
        assert rate == pytest.approx(0.0, abs=1e-9)

    def test_trend_single_value_returns_stable(self):
        direction, rate = calculate_trend([0.35])
        assert direction == "stable"
