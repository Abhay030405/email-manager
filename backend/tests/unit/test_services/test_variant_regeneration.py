"""Unit tests for VariantRegenerationService (unit/test_services version)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.performance_scoring_service import PerformanceScoringService
from app.services.variant_regeneration_service import VariantRegenerationService


def _make_svc() -> VariantRegenerationService:
    metrics_repo = MagicMock()
    variant_repo = MagicMock()
    scoring_svc = PerformanceScoringService(metrics_repo=metrics_repo, variant_repo=variant_repo)

    iteration_repo = MagicMock()
    iteration_repo.create = AsyncMock(side_effect=lambda it: it)

    variant_repo_mock = MagicMock()
    variant_repo_mock.find_by_id = AsyncMock(return_value=None)

    return VariantRegenerationService(
        performance_scoring_service=scoring_svc,
        variant_iteration_repo=iteration_repo,
        variant_repo=variant_repo_mock,
    )


@pytest.mark.unit
class TestVariantRegenerationService:

    async def test_generate_candidates_returns_list(self):
        svc = _make_svc()
        candidates = await svc.generate_variant_candidates(
            segment_name="premium",
            previous_subject="Old subject line here",
            previous_body="Old body content here for the email.",
            optimization_factors=["urgency"],
            num_candidates=3,
        )
        assert isinstance(candidates, list)
        assert len(candidates) == 3

    async def test_generate_candidates_have_required_fields(self):
        svc = _make_svc()
        candidates = await svc.generate_variant_candidates(
            "standard", "Subject", "Body", [], num_candidates=1
        )
        c = candidates[0]
        assert "subject_line" in c
        assert "email_body" in c
        assert "send_time" in c

    async def test_select_best_variant_returns_best(self):
        svc = _make_svc()
        candidates = [
            {"subject_line": "Hi", "email_body": "short", "send_time": None},
            {
                "subject_line": "Exclusive deal: save 30% this week only!",
                "email_body": "word " * 150 + " click here to learn more",
                "send_time": None,
            },
        ]
        best = await svc.select_best_variant(candidates)
        assert "content_quality_score" in best

    async def test_select_best_variant_empty_returns_default(self):
        svc = _make_svc()
        result = await svc.select_best_variant([])
        assert "subject_line" in result
        assert "email_body" in result

    async def test_regenerate_variants_skips_missing(self):
        svc = _make_svc()
        poor = [{"variant_id": "missing-var-id", "open_rate": 0.05, "click_rate": 0.01}]
        result = await svc.regenerate_variants("camp-001", poor, [], iteration_number=1)
        assert result == []

    async def test_track_variant_changes_no_change(self):
        svc = _make_svc()
        iteration = await svc.track_variant_changes(
            campaign_id="camp-001",
            variant_id="var-001",
            iteration_number=1,
            previous_variant={"subject_line": "Same", "email_body": "Same body"},
            new_variant={"subject_line": "Same", "email_body": "Same body"},
            improvements_applied=[],
        )
        assert iteration.changes == {}
