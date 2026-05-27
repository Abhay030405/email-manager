"""A/B testing service — statistical comparison of two campaign variants."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from app.db.repositories.ab_test_repo import ABTestRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.models.ab_test import ABTest
from app.utils.statistical_analysis import (
    calculate_confidence_interval,
    calculate_sample_size,
    calculate_statistical_power,
    perform_statistical_test,
)

logger = logging.getLogger(__name__)

_MIN_SAMPLE = 30  # minimum customers per variant before declaring significance


class ABTestingService:
    """Creates, runs, and analyses A/B tests for campaign variants."""

    def __init__(
        self,
        ab_test_repo: ABTestRepository,
        metrics_repo: MetricsRepository,
    ) -> None:
        self.ab_test_repo = ab_test_repo
        self.metrics_repo = metrics_repo

    # ── Setup ─────────────────────────────────────────────────────────────────

    async def setup_ab_test(
        self,
        campaign_id: str,
        variant_a_id: str,
        variant_b_id: str,
        test_duration_hours: int = 24,
    ) -> ABTest:
        """Create and persist an A/B test record."""
        now = datetime.utcnow()
        test = ABTest(
            campaign_id=campaign_id,
            variant_a_id=variant_a_id,
            variant_b_id=variant_b_id,
            test_start_time=now,
            test_end_time=now + timedelta(hours=test_duration_hours),
            test_duration_hours=test_duration_hours,
        )
        return await self.ab_test_repo.create(test)

    # ── Analysis ──────────────────────────────────────────────────────────────

    async def analyze_test_results(
        self,
        variant_a_metrics: dict[str, Any],
        variant_b_metrics: dict[str, Any],
        sample_a: list[dict[str, Any]] | None = None,
        sample_b: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Statistically compare two variant metric dicts."""
        sample_a = sample_a or []
        sample_b = sample_b or []

        open_rate_a = float(variant_a_metrics.get("open_rate", 0.0))
        open_rate_b = float(variant_b_metrics.get("open_rate", 0.0))
        click_rate_a = float(variant_a_metrics.get("click_rate", 0.0))
        click_rate_b = float(variant_b_metrics.get("click_rate", 0.0))

        # Normalise to 0-1 if stored as percentage
        if open_rate_a > 1:
            open_rate_a /= 100
        if open_rate_b > 1:
            open_rate_b /= 100
        if click_rate_a > 1:
            click_rate_a /= 100
        if click_rate_b > 1:
            click_rate_b /= 100

        n_a = int(variant_a_metrics.get("total_sent", len(sample_a)))
        n_b = int(variant_b_metrics.get("total_sent", len(sample_b)))

        opens_a = int(round(open_rate_a * n_a))
        opens_b = int(round(open_rate_b * n_b))

        # Statistical test on open rate
        stat_result = perform_statistical_test(
            [opens_a, n_a], [opens_b, n_b], confidence_level=0.95
        )

        # CIs
        ci_a = calculate_confidence_interval(n_a, open_rate_a)
        ci_b = calculate_confidence_interval(n_b, open_rate_b)

        # Winner
        winner: Optional[str] = None
        lift = 0.0
        if stat_result["is_significant"] and n_a >= _MIN_SAMPLE and n_b >= _MIN_SAMPLE:
            if open_rate_a > open_rate_b:
                winner = "variant_a"
                lift = ((open_rate_a - open_rate_b) / open_rate_b * 100) if open_rate_b > 0 else 0.0
            else:
                winner = "variant_b"
                lift = ((open_rate_b - open_rate_a) / open_rate_a * 100) if open_rate_a > 0 else 0.0

        # Power
        power = calculate_statistical_power(
            min(n_a, n_b), open_rate_a, open_rate_b
        )

        recommendation = _build_recommendation(winner, stat_result["is_significant"], n_a, n_b, lift)

        return {
            "is_significant": stat_result["is_significant"],
            "p_value": stat_result["p_value"],
            "winner": winner,
            "lift": round(lift, 2),
            "confidence_level": 0.95,
            "ci_a": ci_a,
            "ci_b": ci_b,
            "statistical_power": power,
            "recommendation": recommendation,
        }

    async def run_ab_test(self, test_id: str) -> ABTest:
        """Fetch current metrics and update test results."""
        test = await self.ab_test_repo.find_by_id(test_id)
        if not test:
            raise ValueError(f"A/B test {test_id} not found")

        metrics_a = await self.metrics_repo.find_by_variant(test.variant_a_id)
        metrics_b = await self.metrics_repo.find_by_variant(test.variant_b_id)

        a_dict = metrics_a.model_dump() if metrics_a else {}
        b_dict = metrics_b.model_dump() if metrics_b else {}

        analysis = await self.analyze_test_results(a_dict, b_dict)
        n_a = int(a_dict.get("total_sent", 0))
        n_b = int(b_dict.get("total_sent", 0))

        updates = {
            "total_customers_a": n_a,
            "total_customers_b": n_b,
            "variant_a_metrics": a_dict,
            "variant_b_metrics": b_dict,
            "p_value": analysis["p_value"],
            "is_significant": analysis["is_significant"],
            "winner": analysis["winner"],
            "lift": analysis["lift"],
            "recommendation": analysis["recommendation"],
            "statistical_power": analysis["statistical_power"],
        }
        return await self.ab_test_repo.update_results(test_id, updates)

    async def recommend_winning_variant(self, test: ABTest) -> dict[str, Any]:
        """Return a structured recommendation from a completed test."""
        if not test.is_significant:
            next_steps = [
                "Collect more data — current sample size may be insufficient",
                f"Required minimum: {calculate_sample_size(0.25, 0.10)} customers per variant",
                "Consider running the test for a longer duration",
            ]
            return {
                "winner": None,
                "recommendation": "No statistically significant winner yet",
                "next_steps": next_steps,
            }

        winner_id = test.variant_a_id if test.winner == "variant_a" else test.variant_b_id
        loser_id = test.variant_b_id if test.winner == "variant_a" else test.variant_a_id
        next_steps = [
            f"Scale winning variant {winner_id} to full audience",
            f"Pause or retire losing variant {loser_id}",
            f"Expected lift of {test.lift:.1f}% in open rate",
            "Run another optimization iteration with the winning content as baseline",
        ]
        return {
            "winner": winner_id,
            "recommendation": f"Variant '{test.winner}' outperforms by {test.lift:.1f}%. "
                              f"p-value={test.p_value:.4f} (significant at 95% confidence).",
            "next_steps": next_steps,
        }


# ── Pure helper ───────────────────────────────────────────────────────────────

def _build_recommendation(
    winner: Optional[str],
    is_significant: bool,
    n_a: int,
    n_b: int,
    lift: float,
) -> str:
    if not is_significant:
        if n_a < _MIN_SAMPLE or n_b < _MIN_SAMPLE:
            return f"Insufficient sample size (A={n_a}, B={n_b}). Need at least {_MIN_SAMPLE} per variant."
        return "Results are not statistically significant. Collect more data before deciding."
    if winner == "variant_a":
        return f"Variant A is the winner with {lift:.1f}% lift. Scale Variant A to full audience."
    if winner == "variant_b":
        return f"Variant B is the winner with {lift:.1f}% lift. Scale Variant B to full audience."
    return "Test completed but no clear winner identified."
