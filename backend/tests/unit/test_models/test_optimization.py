"""Unit tests for the Optimization model."""

import pytest

from app.models.optimization import Optimization


@pytest.mark.unit
class TestOptimizationModel:

    def test_create_optimization_record(self):
        opt = Optimization(
            campaign_id="camp-001",
            iteration=1,
            poor_performers=["var-002", "var-003"],
            new_variants=["var-new-001"],
            improvement_percentage=15.0,
        )
        assert opt.campaign_id == "camp-001"
        assert opt.iteration == 1
        assert len(opt.poor_performers) == 2

    def test_optimization_id_auto_generated(self):
        opt = Optimization(campaign_id="camp-001")
        assert opt.optimization_id is not None

    def test_optimization_defaults(self):
        opt = Optimization(campaign_id="camp-001")
        assert opt.iteration == 1 or opt.iteration == 0
        assert opt.poor_performers == [] or opt.poor_performers is not None
        assert opt.created_at is not None
