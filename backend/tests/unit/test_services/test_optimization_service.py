"""Unit tests for OptimizationService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.optimization import OptimizationResult
from app.services.ab_testing_service import ABTestingService
from app.services.optimization_service import OptimizationService
from app.services.performance_scoring_service import PerformanceScoringService
from app.services.variant_regeneration_service import VariantRegenerationService


def _make_svc(poor_performers=None, improvement_potential=0.5, metrics_list=None):
    agent = MagicMock()
    agent.analyze_optimization_opportunity = AsyncMock(return_value={
        "overall_performance": 0.20,
        "poor_performers": poor_performers if poor_performers is not None else [
            {"variant_id": "v1", "open_rate": 0.10, "click_rate": 0.02},
        ],
        "segment_analysis": {},
        "optimization_factors": ["low_open_rate"],
        "improvement_potential": improvement_potential,
    })
    agent.generate_optimization_insights = AsyncMock(return_value=[
        {"type": "content", "variant_id": "v1", "issue": "low open", "recommendation": "Add urgency"},
    ])
    agent.check_convergence = AsyncMock(return_value=False)

    m = MagicMock()
    m.model_dump.return_value = {"variant_id": "v1", "open_rate": 0.10, "click_rate": 0.02}

    metrics_repo = MagicMock()
    metrics_repo.find_by_campaign = AsyncMock(return_value=metrics_list if metrics_list is not None else [m])

    regen = MagicMock()
    regen.regenerate_variants = AsyncMock(return_value=[
        {"variant_id": "v-new", "subject_line": "Better", "email_body": "Better body"},
    ])

    ab_svc = MagicMock()
    ab_mock = MagicMock()
    ab_mock.test_id = "test-001"
    ab_svc.setup_ab_test = AsyncMock(return_value=ab_mock)

    opt_repo = MagicMock()
    opt_repo.create = AsyncMock(side_effect=lambda r: r)
    opt_repo.update = AsyncMock(return_value=None)
    opt_repo.list_by_campaign = AsyncMock(return_value=[])

    return OptimizationService(
        optimization_agent=agent,
        variant_regeneration_service=regen,
        ab_testing_service=ab_svc,
        performance_scoring_service=MagicMock(),
        optimization_repo=opt_repo,
        metrics_repo=metrics_repo,
    )


@pytest.mark.unit
class TestOptimizationService:

    async def test_full_workflow_returns_required_keys(self):
        svc = _make_svc()
        result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=1)
        for key in ("campaign_id", "iterations_completed", "converged", "final_performance"):
            assert key in result

    async def test_full_workflow_empty_metrics_stops(self):
        svc = _make_svc(metrics_list=[])
        result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=3)
        assert result["variants_improved"] == 0

    async def test_full_workflow_no_poor_performers_stops(self):
        svc = _make_svc(poor_performers=[])
        result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=3)
        assert result["iterations_completed"] <= 1

    async def test_full_workflow_low_potential_converges(self):
        svc = _make_svc(improvement_potential=0.05)
        result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=3)
        assert result["converged"] is True

    async def test_full_workflow_respects_max_iterations(self):
        svc = _make_svc()
        result = await svc.execute_full_optimization_workflow("camp-001", max_iterations=2)
        assert result["iterations_completed"] <= 2

    async def test_full_workflow_campaign_id_propagated(self):
        svc = _make_svc()
        result = await svc.execute_full_optimization_workflow("my-campaign", max_iterations=1)
        assert result["campaign_id"] == "my-campaign"

    async def test_full_workflow_ab_testing_disabled(self):
        svc = _make_svc()
        result = await svc.execute_full_optimization_workflow(
            "camp-001", max_iterations=1, enable_ab_testing=False
        )
        svc.ab_testing_svc.setup_ab_test.assert_not_called()
        assert result["campaign_id"] == "camp-001"

    async def test_full_workflow_opt_repo_called(self):
        svc = _make_svc()
        await svc.execute_full_optimization_workflow("camp-001", max_iterations=1)
        svc.optimization_repo.create.assert_called()
