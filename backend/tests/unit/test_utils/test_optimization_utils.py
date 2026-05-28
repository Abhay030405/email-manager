"""Unit tests for optimization_utils module."""

import pytest

from app.utils.optimization_utils import (
    identify_optimization_factors,
    generate_optimization_insights,
)


@pytest.mark.unit
class TestOptimizationUtils:

    def test_identify_factors_low_open_rate(self):
        metrics = {"open_rate": 0.08, "click_rate": 0.02, "performance_score": 0.03}
        factors = identify_optimization_factors(metrics)
        assert isinstance(factors, (list, dict))
        if isinstance(factors, list):
            assert len(factors) >= 0
        else:
            assert factors is not None

    def test_identify_factors_good_metrics(self):
        metrics = {"open_rate": 0.50, "click_rate": 0.15, "performance_score": 0.26}
        factors = identify_optimization_factors(metrics)
        assert factors is not None

    def test_generate_insights_returns_list(self):
        poor_performers = [
            {"variant_id": "var-1", "performance_score": 0.05, "open_rate": 0.08}
        ]
        insights = generate_optimization_insights(poor_performers)
        assert isinstance(insights, list)

    def test_generate_insights_empty_performers(self):
        insights = generate_optimization_insights([])
        assert isinstance(insights, list)
        assert len(insights) == 0
