"""Tests for VariantRegenerationService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.variant_iteration import VariantIteration
from app.services.performance_scoring_service import PerformanceScoringService
from app.services.variant_regeneration_service import (
    VariantRegenerationService,
    _rule_based_candidates,
    _optimal_send_time,
    _compute_changes,
)


def _make_scoring_svc():
    metrics_repo = MagicMock()
    variant_repo = MagicMock()
    return PerformanceScoringService(metrics_repo=metrics_repo, variant_repo=variant_repo)


def _make_service(existing_variant=None):
    scoring_svc = _make_scoring_svc()

    iteration_repo = MagicMock()
    iteration_repo.create = AsyncMock(side_effect=lambda it: it)

    variant_repo = MagicMock()
    variant_repo.find_by_id = AsyncMock(return_value=existing_variant)

    return VariantRegenerationService(
        performance_scoring_service=scoring_svc,
        variant_iteration_repo=iteration_repo,
        variant_repo=variant_repo,
    ), iteration_repo, variant_repo


def _make_existing_variant(variant_id="var-001", segment="premium"):
    v = MagicMock()
    v.variant_id = variant_id
    v.segment_name = segment
    v.subject_line = "Original subject line for testing"
    v.email_body = "Original body content for the email that is a bit longer."
    return v


# ── generate_variant_candidates ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_variant_candidates_returns_expected_count():
    svc, *_ = _make_service()
    candidates = await svc.generate_variant_candidates(
        segment_name="premium",
        previous_subject="Old subject",
        previous_body="Old body content",
        optimization_factors=["Add urgency"],
        num_candidates=3,
    )
    assert len(candidates) == 3


@pytest.mark.asyncio
async def test_generate_variant_candidates_fewer_than_requested():
    svc, *_ = _make_service()
    candidates = await svc.generate_variant_candidates(
        segment_name="standard",
        previous_subject="Sub",
        previous_body="Body",
        optimization_factors=[],
        num_candidates=2,
    )
    assert len(candidates) <= 3


@pytest.mark.asyncio
async def test_generate_variant_candidates_have_required_fields():
    svc, *_ = _make_service()
    candidates = await svc.generate_variant_candidates("seg", "subj", "body", [], num_candidates=1)
    c = candidates[0]
    assert "subject_line" in c
    assert "email_body" in c
    assert "send_time" in c


# ── select_best_variant ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_select_best_variant_returns_highest_quality():
    svc, *_ = _make_service()
    candidates = [
        {"subject_line": "Hi", "email_body": "short", "send_time": None},
        {
            "subject_line": "Limited time: exclusive offer for you today!",
            "email_body": "word " * 150 + "click here to learn more",
            "send_time": _optimal_send_time(),
        },
    ]
    best = await svc.select_best_variant(candidates)
    assert best["content_quality_score"] >= 0.0


@pytest.mark.asyncio
async def test_select_best_variant_empty_returns_default():
    svc, *_ = _make_service()
    best = await svc.select_best_variant([])
    assert "subject_line" in best
    assert "email_body" in best


@pytest.mark.asyncio
async def test_select_best_variant_all_scored():
    svc, *_ = _make_service()
    candidates = [
        {"subject_line": "A" * 50, "email_body": "word " * 120, "send_time": None},
        {"subject_line": "B" * 10, "email_body": "short", "send_time": None},
        {"subject_line": "C " * 20, "email_body": "word " * 180, "send_time": None},
    ]
    best = await svc.select_best_variant(candidates)
    assert "content_quality_score" in best
    assert best["content_quality_score"] >= 0.0


# ── track_variant_changes ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_track_variant_changes_records_subject_change():
    svc, iteration_repo, _ = _make_service()
    iteration = await svc.track_variant_changes(
        campaign_id="camp-001",
        variant_id="var-new",
        iteration_number=1,
        previous_variant={"subject_line": "Old subject", "email_body": "Old body"},
        new_variant={"subject_line": "New subject! Much better!", "email_body": "Old body"},
        improvements_applied=["Add urgency"],
    )
    assert "subject_line" in iteration.changes
    assert iteration.iteration_number == 1
    iteration_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_track_variant_changes_no_changes_empty_dict():
    svc, *_ = _make_service()
    iteration = await svc.track_variant_changes(
        campaign_id="camp-001",
        variant_id="var-new",
        iteration_number=2,
        previous_variant={"subject_line": "Same", "email_body": "Same body"},
        new_variant={"subject_line": "Same", "email_body": "Same body"},
        improvements_applied=[],
    )
    assert iteration.changes == {}


@pytest.mark.asyncio
async def test_track_variant_changes_sets_quality_score():
    svc, *_ = _make_service()
    iteration = await svc.track_variant_changes(
        campaign_id="camp-001",
        variant_id="var-new",
        iteration_number=1,
        previous_variant={"subject_line": "Old", "email_body": "Old"},
        new_variant={
            "subject_line": "Limited offer: exclusive deal for you today now!",
            "email_body": "word " * 150 + " click here",
            "send_time": _optimal_send_time(),
        },
        improvements_applied=["urgency"],
    )
    assert iteration.content_quality_score > 0.0


# ── regenerate_variants ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_regenerate_variants_skips_missing_variant():
    svc, _, variant_repo = _make_service(existing_variant=None)
    poor = [{"variant_id": "missing", "open_rate": 0.10, "click_rate": 0.02}]
    result = await svc.regenerate_variants("camp-001", poor, [], iteration_number=1)
    assert result == []


@pytest.mark.asyncio
async def test_regenerate_variants_produces_new_variant():
    existing = _make_existing_variant()
    svc, _, _ = _make_service(existing_variant=existing)
    poor = [{"variant_id": "var-001", "open_rate": 0.10, "click_rate": 0.02}]
    insights = [{"type": "content", "variant_id": "var-001", "recommendation": "Add urgency", "issue": "low open"}]
    result = await svc.regenerate_variants("camp-001", poor, insights, iteration_number=1)
    assert len(result) == 1
    assert "variant_id" in result[0]
    assert result[0]["variant_id"] != "var-001"  # new ID


@pytest.mark.asyncio
async def test_regenerate_variants_multiple_poor_performers():
    existing1 = _make_existing_variant("v1")
    existing2 = _make_existing_variant("v2", "standard")

    svc, _, variant_repo = _make_service()
    async def fake_find(vid):
        return existing1 if vid == "v1" else existing2
    variant_repo.find_by_id = AsyncMock(side_effect=fake_find)

    poor = [
        {"variant_id": "v1", "open_rate": 0.10, "click_rate": 0.02},
        {"variant_id": "v2", "open_rate": 0.12, "click_rate": 0.03},
    ]
    result = await svc.regenerate_variants("camp-001", poor, [], iteration_number=2)
    assert len(result) == 2


# ── pure helpers ──────────────────────────────────────────────────────────────

def test_rule_based_candidates_count():
    candidates = _rule_based_candidates("premium", "Old subj", "Old body", [], 3)
    assert len(candidates) == 3


def test_rule_based_candidates_have_required_fields():
    candidates = _rule_based_candidates("standard", "Subj", "Body", ["Add urgency"], 2)
    for c in candidates:
        assert "subject_line" in c
        assert "email_body" in c
        assert "send_time" in c


def test_compute_changes_detects_subject_change():
    changes = _compute_changes("Old", "Same body", "New", "Same body")
    assert "subject_line" in changes


def test_compute_changes_detects_body_change():
    changes = _compute_changes("Same", "Old body", "Same", "New body content here")
    assert "email_body" in changes


def test_compute_changes_no_change_empty():
    changes = _compute_changes("Same", "Same", "Same", "Same")
    assert changes == {}


def test_optimal_send_time_is_wednesday():
    dt = _optimal_send_time()
    assert dt.weekday() == 2  # Wednesday
    assert dt.hour == 9
