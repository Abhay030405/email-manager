"""Unit tests for optimization_utils module."""

import pytest

from app.utils.optimization_utils import (
    build_improvement_prompt_context,
    generate_optimization_insights,
    identify_optimization_factors,
)


@pytest.mark.unit
class TestOptimizationUtils:

    # ── identify_optimization_factors ─────────────────────────────

    def test_identify_factors_low_open_rate(self):
        metrics = {"open_rate": 0.08, "click_rate": 0.02}
        factors = identify_optimization_factors(metrics, customer_results=[])
        assert isinstance(factors, list)
        assert len(factors) > 0

    def test_identify_factors_good_metrics_fewer_flags(self):
        metrics = {"open_rate": 0.50, "click_rate": 0.15}
        factors = identify_optimization_factors(metrics, customer_results=[])
        assert isinstance(factors, list)

    def test_identify_factors_empty_metrics(self):
        factors = identify_optimization_factors({}, customer_results=[])
        assert isinstance(factors, list)

    def test_identify_factors_with_customer_results(self):
        customers = [{"opened": False, "open_probability": 0.1}] * 8 + [{"opened": True}] * 2
        factors = identify_optimization_factors({"open_rate": 0.15}, customer_results=customers)
        assert isinstance(factors, list)

    def test_identify_factors_percent_and_decimal_same_result(self):
        decimal = identify_optimization_factors({"open_rate": 0.10, "click_rate": 0.02}, [])
        percent = identify_optimization_factors({"open_rate": 10.0, "click_rate": 2.0}, [])
        assert set(decimal) == set(percent)

    # ── generate_optimization_insights ───────────────────────────

    def test_generate_insights_returns_list(self):
        poor = [{"variant_id": "v-1", "open_rate": 0.08, "performance_score": 0.03}]
        insights = generate_optimization_insights(poor, segment_performance={}, customer_results=[])
        assert isinstance(insights, list)

    def test_generate_insights_empty_performers(self):
        insights = generate_optimization_insights([], segment_performance={}, customer_results=[])
        assert isinstance(insights, list)
        assert len(insights) == 0

    def test_generate_insights_have_required_fields(self):
        poor = [{"variant_id": "v-1", "open_rate": 0.05, "click_rate": 0.005}]
        insights = generate_optimization_insights(poor, {}, [])
        for insight in insights:
            assert "type" in insight
            assert "recommendation" in insight
            assert "issue" in insight

    def test_generate_insights_multiple_poor_performers(self):
        poor = [
            {"variant_id": "v-1", "open_rate": 0.05},
            {"variant_id": "v-2", "open_rate": 0.06},
        ]
        insights = generate_optimization_insights(poor, {}, [])
        assert isinstance(insights, list)

    # ── build_improvement_prompt_context ─────────────────────────

    def test_build_context_returns_dict(self):
        variant = {"variant_id": "v1", "subject_line": "Hi", "email_body": "Body"}
        result = build_improvement_prompt_context(variant, insights=[])
        assert isinstance(result, dict)

    def test_build_context_has_required_keys(self):
        variant = {"variant_id": "v1", "subject_line": "Hello", "email_body": "Content"}
        result = build_improvement_prompt_context(variant, insights=[])
        for key in ("previous_subject", "previous_body", "optimization_requirements", "must_improve"):
            assert key in result

    def test_build_context_with_insights(self):
        variant = {"variant_id": "v1", "subject_line": "Hi", "email_body": "Short"}
        insights = [{"type": "content", "issue": "low open", "recommendation": "Add urgency"}]
        result = build_improvement_prompt_context(variant, insights)
        assert isinstance(result, dict)
        assert len(result["must_improve"]) > 0

    def test_build_context_empty_variant(self):
        result = build_improvement_prompt_context({}, insights=[])
        assert isinstance(result, dict)
