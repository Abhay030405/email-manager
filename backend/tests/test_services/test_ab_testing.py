"""Tests for ABTestingService."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ab_test import ABTest
from app.services.ab_testing_service import ABTestingService


def _make_service(existing_test=None):
    ab_test_repo = MagicMock()
    ab_test_repo.create = AsyncMock(side_effect=lambda t: t)
    ab_test_repo.find_by_id = AsyncMock(return_value=existing_test)

    async def fake_update(test_id, updates):
        if existing_test:
            for k, v in updates.items():
                setattr(existing_test, k, v)
            return existing_test
        return None

    ab_test_repo.update_results = AsyncMock(side_effect=fake_update)

    metrics_repo = MagicMock()
    metrics_repo.find_by_variant = AsyncMock(return_value=None)

    return ABTestingService(ab_test_repo=ab_test_repo, metrics_repo=metrics_repo), ab_test_repo, metrics_repo


def _make_test(**kwargs) -> ABTest:
    defaults = dict(
        campaign_id="camp-001",
        variant_a_id="var-a",
        variant_b_id="var-b",
        test_duration_hours=24,
        total_customers_a=500,
        total_customers_b=500,
        variant_a_metrics={"open_rate": 0.35, "click_rate": 0.08, "total_sent": 500},
        variant_b_metrics={"open_rate": 0.25, "click_rate": 0.06, "total_sent": 500},
        p_value=0.02,
        is_significant=True,
        winner="variant_a",
        lift=40.0,
        recommendation="Variant A wins",
        statistical_power=0.8,
    )
    defaults.update(kwargs)
    return ABTest(**defaults)


# ── setup_ab_test ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_setup_ab_test_creates_record():
    svc, repo, _ = _make_service()
    test = await svc.setup_ab_test("camp-001", "var-a", "var-b", test_duration_hours=24)
    assert test.campaign_id == "camp-001"
    assert test.variant_a_id == "var-a"
    assert test.variant_b_id == "var-b"
    assert test.test_duration_hours == 24
    repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_setup_ab_test_sets_end_time():
    svc, *_ = _make_service()
    test = await svc.setup_ab_test("camp-001", "var-a", "var-b", test_duration_hours=48)
    delta = test.test_end_time - test.test_start_time
    assert abs(delta.total_seconds() - 48 * 3600) < 5


# ── analyze_test_results ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_test_results_significant_winner():
    svc, *_ = _make_service()
    a = {"open_rate": 0.40, "click_rate": 0.10, "total_sent": 1000}
    b = {"open_rate": 0.20, "click_rate": 0.05, "total_sent": 1000}
    result = await svc.analyze_test_results(a, b)
    assert result["winner"] in ("variant_a", None)
    assert "p_value" in result
    assert "lift" in result


@pytest.mark.asyncio
async def test_analyze_test_results_no_winner_when_identical():
    svc, *_ = _make_service()
    same = {"open_rate": 0.30, "click_rate": 0.07, "total_sent": 100}
    result = await svc.analyze_test_results(same, same)
    assert result["is_significant"] is False
    assert result["winner"] is None


@pytest.mark.asyncio
async def test_analyze_test_results_returns_confidence_intervals():
    svc, *_ = _make_service()
    a = {"open_rate": 0.35, "click_rate": 0.08, "total_sent": 500}
    b = {"open_rate": 0.25, "click_rate": 0.06, "total_sent": 500}
    result = await svc.analyze_test_results(a, b)
    assert "ci_a" in result
    assert "ci_b" in result
    assert len(result["ci_a"]) == 2


@pytest.mark.asyncio
async def test_analyze_test_results_percentage_rates_normalised():
    svc, *_ = _make_service()
    # Rates given as 0-100 (percentage style)
    a = {"open_rate": 40.0, "click_rate": 10.0, "total_sent": 500}
    b = {"open_rate": 20.0, "click_rate": 5.0, "total_sent": 500}
    result = await svc.analyze_test_results(a, b)
    assert "p_value" in result


@pytest.mark.asyncio
async def test_analyze_test_results_insufficient_sample():
    svc, *_ = _make_service()
    a = {"open_rate": 0.40, "click_rate": 0.10, "total_sent": 10}
    b = {"open_rate": 0.20, "click_rate": 0.05, "total_sent": 10}
    result = await svc.analyze_test_results(a, b)
    # Small samples should not declare a winner
    assert result["winner"] is None


# ── run_ab_test ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_ab_test_not_found_raises():
    svc, ab_repo, _ = _make_service(existing_test=None)
    ab_repo.find_by_id = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="not found"):
        await svc.run_ab_test("missing-id")


@pytest.mark.asyncio
async def test_run_ab_test_updates_results():
    test = _make_test()
    svc, ab_repo, metrics_repo = _make_service(existing_test=test)

    from tests.test_services.conftest import make_metrics
    m_a = make_metrics(variant_id="var-a", open_rate=0.35, click_rate=0.08, total_sent=500)
    m_b = make_metrics(variant_id="var-b", open_rate=0.25, click_rate=0.06, total_sent=500)

    async def fake_find(variant_id):
        return m_a if variant_id == "var-a" else m_b

    metrics_repo.find_by_variant = AsyncMock(side_effect=fake_find)
    result = await svc.run_ab_test(test.test_id)
    ab_repo.update_results.assert_called_once()
    assert result is not None


# ── recommend_winning_variant ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recommend_winning_variant_significant():
    svc, *_ = _make_service()
    test = _make_test(is_significant=True, winner="variant_b", lift=20.0, p_value=0.01)
    rec = await svc.recommend_winning_variant(test)
    assert rec["winner"] == test.variant_b_id
    assert len(rec["next_steps"]) > 0


@pytest.mark.asyncio
async def test_recommend_winning_variant_not_significant():
    svc, *_ = _make_service()
    test = _make_test(is_significant=False, winner=None, lift=0.0, p_value=0.30)
    rec = await svc.recommend_winning_variant(test)
    assert rec["winner"] is None
    assert "more data" in rec["recommendation"].lower() or "no" in rec["recommendation"].lower()


@pytest.mark.asyncio
async def test_recommend_winning_variant_next_steps_present():
    svc, *_ = _make_service()
    test = _make_test(is_significant=True, winner="variant_a", lift=15.0)
    rec = await svc.recommend_winning_variant(test)
    assert isinstance(rec["next_steps"], list)
    assert len(rec["next_steps"]) >= 1
