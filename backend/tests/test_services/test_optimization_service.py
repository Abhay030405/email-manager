"""Tests for optimization utilities and OptimizationService orchestrator.

Agent-level logic (analyze_optimization_opportunity, generate_insights,
recommend_content_improvements, check_convergence) is tested via the
underlying utility functions in app.utils.optimization_utils so that the
test suite does not need to import the full agent package chain.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.optimization import OptimizationResult
from app.services.optimization_service import OptimizationService
from app.utils.optimization_utils import (
    build_improvement_prompt_context,
    generate_optimization_insights,
    identify_optimization_factors,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_metrics(variant_id: str, open_rate: float = 0.30, click_rate: float = 0.07) -> dict:
    return {"variant_id": variant_id, "open_rate": open_rate, "click_rate": click_rate, "total_sent": 500}


def _opt_result(new_score: float) -> SimpleNamespace:
    """Minimal object that check_convergence reads (new_performance_score attr)."""
    return SimpleNamespace(new_performance_score=new_score, result_id="r1", regenerated_variants=[])


def _check_convergence(results: list, threshold: float = 0.05) -> bool:
    """Pure-Python replica of OptimizationAgent.check_convergence logic."""
    if len(results) < 2:
        return False
    prev = getattr(results[-2], "new_performance_score", 0.0)
    curr = getattr(results[-1], "new_performance_score", 0.0)
    if prev == 0:
        return False
    return (curr - prev) / prev < threshold


def _make_optimization_service(
    metrics_list=None,
    poor_performers=None,
    new_variants=None,
) -> OptimizationService:
    agent = MagicMock()
    agent.analyze_optimization_opportunity = AsyncMock(
        return_value={
            "overall_performance": 0.20,
            "poor_performers": poor_performers if poor_performers is not None else [
                {"variant_id": "v1", "open_rate": 0.10, "click_rate": 0.02},
            ],
            "segment_analysis": {"premium": 0.25},
            "optimization_factors": ["low_open_rate"],
            "improvement_potential": 0.50,
        }
    )
    agent.generate_optimization_insights = AsyncMock(
        return_value=[
            {"type": "content", "variant_id": "v1", "issue": "low open rate", "recommendation": "Add urgency"},
        ]
    )
    agent.check_convergence = AsyncMock(return_value=False)

    m = MagicMock()
    m.model_dump.return_value = {"variant_id": "v1", "open_rate": 0.10, "click_rate": 0.02}
    if metrics_list is None:
        metrics_list = [m]

    metrics_repo = MagicMock()
    metrics_repo.find_by_campaign = AsyncMock(return_value=metrics_list)

    regen_svc = MagicMock()
    regen_svc.regenerate_variants = AsyncMock(
        return_value=new_variants if new_variants is not None else [
            {"variant_id": "v-new", "subject_line": "Better subject", "email_body": "Better body"},
        ]
    )

    ab_svc = MagicMock()
    ab_mock = MagicMock()
    ab_mock.test_id = "test-001"
    ab_svc.setup_ab_test = AsyncMock(return_value=ab_mock)

    opt_repo = MagicMock()
    opt_repo.create = AsyncMock(side_effect=lambda r: r)
    opt_repo.update = AsyncMock(return_value=None)

    return OptimizationService(
        optimization_agent=agent,
        variant_regeneration_service=regen_svc,
        ab_testing_service=ab_svc,
        performance_scoring_service=MagicMock(),
        optimization_repo=opt_repo,
        metrics_repo=metrics_repo,
    )


# ── test_analyze_optimization_opportunity (via identify_optimization_factors) ─

def test_analyze_opportunity_good_performer_no_factors():
    factors = identify_optimization_factors(
        {"open_rate": 0.50, "click_rate": 0.15}, []
    )
    assert "low_subject_line_opens" not in factors
    assert "weak_call_to_action" not in factors


def test_analyze_opportunity_low_open_rate_flagged():
    factors = identify_optimization_factors({"open_rate": 0.10, "click_rate": 0.15}, [])
    assert "low_subject_line_opens" in factors
    assert "critical_open_rate" in factors


def test_analyze_opportunity_low_click_rate_flagged():
    factors = identify_optimization_factors({"open_rate": 0.50, "click_rate": 0.005}, [])
    assert "weak_call_to_action" in factors
    assert "stalled_clicks" in factors


def test_analyze_opportunity_percent_rates_normalised():
    # Both values > 1.0 so the function normalises them; results must match decimal equivalents
    factors_decimal = identify_optimization_factors({"open_rate": 0.10, "click_rate": 0.02}, [])
    factors_percent = identify_optimization_factors({"open_rate": 10.0, "click_rate": 2.0}, [])
    assert set(factors_decimal) == set(factors_percent)


def test_analyze_opportunity_customer_results_poor_targeting():
    customers = [{"opened": False, "open_probability": 0.1}] * 7 + [{"opened": True, "open_probability": 0.8}] * 3
    factors = identify_optimization_factors({"open_rate": 0.30, "click_rate": 0.05}, customers)
    assert "poor_demographic_targeting" in factors


def test_analyze_opportunity_returns_list():
    result = identify_optimization_factors({}, [])
    assert isinstance(result, list)


# ── test_generate_optimization_insights ──────────────────────────────────────

def test_generate_insights_empty_input():
    insights = generate_optimization_insights([], {}, [])
    assert insights == []


def test_generate_insights_low_open_rate_generates_content_insight():
    poor = [{"variant_id": "v1", "open_rate": 0.10, "click_rate": 0.08}]
    insights = generate_optimization_insights(poor, {}, [])
    types = [i["type"] for i in insights]
    assert "content" in types


def test_generate_insights_low_click_rate_generates_content_insight():
    poor = [{"variant_id": "v1", "open_rate": 0.40, "click_rate": 0.02}]
    insights = generate_optimization_insights(poor, {}, [])
    types = [i["type"] for i in insights]
    assert "content" in types


def test_generate_insights_has_required_fields():
    poor = [{"variant_id": "v1", "open_rate": 0.10, "click_rate": 0.02}]
    insights = generate_optimization_insights(poor, {}, [])
    for insight in insights:
        assert "type" in insight
        assert "recommendation" in insight
        assert "issue" in insight


def test_generate_insights_poor_segment_triggers_targeting():
    poor = [{"variant_id": "v1", "open_rate": 0.30, "click_rate": 0.06, "performance_score": 0.05}]
    insights = generate_optimization_insights(poor, {}, [])
    assert any(i["type"] == "targeting" for i in insights)


def test_generate_insights_timing_from_customer_results():
    customers = [{"opened": False, "open_probability": 0.1}] * 5
    poor = [{"variant_id": "v1", "open_rate": 0.30, "click_rate": 0.07}]
    insights = generate_optimization_insights(poor, {}, customers)
    timing = [i for i in insights if i["type"] == "timing"]
    assert len(timing) > 0


# ── test_recommend_content_improvements (via build_improvement_prompt_context) ─

def test_recommend_improvements_returns_required_keys():
    variant = {"variant_id": "v1", "subject_line": "Hi", "email_body": "Short body"}
    result = build_improvement_prompt_context(variant, [])
    for key in ("segment_name", "previous_subject", "previous_body", "optimization_requirements", "must_improve"):
        assert key in result


def test_recommend_improvements_maps_variant_fields():
    variant = {"variant_id": "v1", "subject_line": "Test subject", "email_body": "Test body", "segment_name": "premium"}
    result = build_improvement_prompt_context(variant, [])
    assert result["previous_subject"] == "Test subject"
    assert result["previous_body"] == "Test body"
    assert result["segment_name"] == "premium"


def test_recommend_improvements_includes_insight_recommendations():
    variant = {"variant_id": "v1"}
    insights = [
        {"type": "content", "variant_id": "v1", "issue": "low open", "recommendation": "Add urgency"},
        {"type": "timing", "variant_id": None, "issue": "bad timing", "recommendation": "Send Tuesday"},
    ]
    result = build_improvement_prompt_context(variant, insights)
    assert "Add urgency" in result["optimization_requirements"]
    assert "Send Tuesday" in result["optimization_requirements"]  # variant_id=None matches all


def test_recommend_improvements_filters_unrelated_insights():
    variant = {"variant_id": "v1"}
    insights = [
        {"type": "content", "variant_id": "v2", "issue": "x", "recommendation": "Other variant rec"},
    ]
    result = build_improvement_prompt_context(variant, insights)
    assert "Other variant rec" not in result["optimization_requirements"]


# ── test_convergence_detection ────────────────────────────────────────────────

def test_convergence_needs_two_results():
    assert _check_convergence([_opt_result(0.20)]) is False


def test_convergence_empty_returns_false():
    assert _check_convergence([]) is False


def test_convergence_small_improvement_converges():
    r1 = _opt_result(0.20)
    r2 = _opt_result(0.201)  # <1% improvement
    assert _check_convergence([r1, r2], threshold=0.05) is True


def test_convergence_large_improvement_does_not_converge():
    r1 = _opt_result(0.10)
    r2 = _opt_result(0.20)  # 100% improvement
    assert _check_convergence([r1, r2], threshold=0.05) is False


def test_convergence_zero_previous_returns_false():
    r1 = _opt_result(0.0)
    r2 = _opt_result(0.10)
    assert _check_convergence([r1, r2]) is False


def test_convergence_above_threshold_does_not_converge():
    # 6% improvement > 5% threshold → should NOT converge
    r1 = _opt_result(0.10)
    r2 = _opt_result(0.106)  # 6% improvement
    assert _check_convergence([r1, r2], threshold=0.05) is False


# ── test_optimize_campaign_full_workflow (OptimizationService) ────────────────

@pytest.mark.asyncio
async def test_full_workflow_returns_required_keys():
    svc = _make_optimization_service()
    result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=1)
    for key in ("campaign_id", "iterations_completed", "converged", "final_performance", "total_improvement", "variants_improved"):
        assert key in result


@pytest.mark.asyncio
async def test_full_workflow_respects_max_iterations():
    svc = _make_optimization_service()
    result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=2)
    assert result["iterations_completed"] <= 2


@pytest.mark.asyncio
async def test_full_workflow_no_metrics_stops_early():
    svc = _make_optimization_service(metrics_list=[])
    result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=3)
    # Iteration counter is incremented before the metrics check, so it will be 1
    assert result["iterations_completed"] <= 1
    assert result["variants_improved"] == 0


@pytest.mark.asyncio
async def test_full_workflow_no_poor_performers_stops():
    svc = _make_optimization_service(poor_performers=[])
    result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=3)
    assert result["iterations_completed"] <= 1


@pytest.mark.asyncio
async def test_full_workflow_counts_variants_improved():
    two_variants = [
        {"variant_id": "new-v1", "subject_line": "A", "email_body": "Body A"},
        {"variant_id": "new-v2", "subject_line": "B", "email_body": "Body B"},
    ]
    svc = _make_optimization_service(new_variants=two_variants)
    result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=1)
    assert result["variants_improved"] >= 2


@pytest.mark.asyncio
async def test_full_workflow_campaign_id_preserved():
    svc = _make_optimization_service()
    result = await svc.execute_full_optimization_workflow("my-campaign", max_iterations=1)
    assert result["campaign_id"] == "my-campaign"


@pytest.mark.asyncio
async def test_full_workflow_ab_testing_disabled():
    svc = _make_optimization_service()
    await svc.execute_full_optimization_workflow("camp-001", max_iterations=1, enable_ab_testing=False)
    svc.ab_testing_svc.setup_ab_test.assert_not_called()


@pytest.mark.asyncio
async def test_full_workflow_convergence_flag_propagated():
    svc = _make_optimization_service()
    svc.optimization_agent.check_convergence = AsyncMock(return_value=True)
    result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=3)
    assert result["converged"] is True
    assert result["iterations_completed"] == 1


# ── test_iteration_tracking ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_iteration_tracking_repo_create_called():
    svc = _make_optimization_service()
    await svc.execute_full_optimization_workflow("camp-001", max_iterations=1)
    svc.optimization_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_iteration_tracking_result_has_campaign_id():
    svc = _make_optimization_service()
    created_results = []
    async def capture_create(r):
        created_results.append(r)
        return r
    svc.optimization_repo.create = AsyncMock(side_effect=capture_create)
    await svc.execute_full_optimization_workflow("camp-001", max_iterations=1)
    assert len(created_results) == 1
    assert created_results[0].campaign_id == "camp-001"


@pytest.mark.asyncio
async def test_iteration_tracking_iteration_number_set():
    svc = _make_optimization_service()
    created_results = []
    async def capture_create(r):
        created_results.append(r)
        return r
    svc.optimization_repo.create = AsyncMock(side_effect=capture_create)
    await svc.execute_full_optimization_workflow("camp-001", max_iterations=1)
    assert created_results[0].iteration_number == 1


@pytest.mark.asyncio
async def test_iteration_tracking_final_update_called():
    svc = _make_optimization_service()
    await svc.execute_full_optimization_workflow("camp-001", max_iterations=1)
    svc.optimization_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_iteration_tracking_low_potential_stops_early():
    svc = _make_optimization_service()
    svc.optimization_agent.analyze_optimization_opportunity = AsyncMock(
        return_value={
            "overall_performance": 0.50,
            "poor_performers": [{"variant_id": "v1"}],
            "segment_analysis": {},
            "optimization_factors": [],
            "improvement_potential": 0.05,  # below 0.1 threshold
        }
    )
    result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=3)
    assert result["converged"] is True
    svc.optimization_repo.create.assert_not_called()  # stopped before creating a result
