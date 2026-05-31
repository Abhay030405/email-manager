"""Unit tests for the OptimizationResult model."""

import pytest

from app.models.optimization import OptimizationResult


@pytest.mark.unit
class TestOptimizationModel:

    def test_create_optimization_record(self):
        opt = OptimizationResult(
            campaign_id="camp-001",
            iteration_number=1,
            poor_performer_variants=["var-002", "var-003"],
            regenerated_variants=[{"variant_id": "var-new-001"}],
            improvement_percentage=15.0,
        )
        assert opt.campaign_id == "camp-001"
        assert opt.iteration_number == 1
        assert len(opt.poor_performer_variants) == 2

    def test_optimization_id_auto_generated(self):
        opt = OptimizationResult(campaign_id="camp-001")
        assert opt.result_id is not None
        assert len(opt.result_id) > 0

    def test_optimization_defaults(self):
        opt = OptimizationResult(campaign_id="camp-001")
        assert opt.iteration_number >= 1
        assert opt.poor_performer_variants == []
        assert opt.created_at if hasattr(opt, "created_at") else opt.execution_timestamp is not None

    def test_optimization_status_default(self):
        opt = OptimizationResult(campaign_id="camp-001")
        assert opt.status in ("pending", "completed", "failed")

    def test_optimization_convergence_default(self):
        opt = OptimizationResult(campaign_id="camp-001")
        assert opt.convergence_achieved is False

    def test_optimization_performance_scores_default_zero(self):
        opt = OptimizationResult(campaign_id="camp-001")
        assert opt.previous_performance_score == 0.0
        assert opt.new_performance_score == 0.0
        assert opt.improvement_percentage == 0.0
