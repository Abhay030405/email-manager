"""Performance scoring service — scores, ranks, and compares campaign variant metrics."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.variant_repo import VariantRepository

logger = logging.getLogger(__name__)


class PerformanceScoringService:
    """Calculate and analyse performance scores for campaign variants."""

    def __init__(
        self,
        metrics_repo: MetricsRepository,
        variant_repo: VariantRepository,
    ) -> None:
        self.metrics_repo = metrics_repo
        self.variant_repo = variant_repo

    # ── Scoring ───────────────────────────────────────────────────────────────

    def calculate_performance_score(
        self,
        open_rate: float,
        click_rate: float,
    ) -> float:
        """Return performance_score in [0, 1].

        Accepts rates as percentages (0-100) and normalises internally.
        Formula: 0.7 * (click_rate/100) + 0.3 * (open_rate/100)
        """
        click_norm = max(0.0, min(click_rate / 100.0, 1.0))
        open_norm = max(0.0, min(open_rate / 100.0, 1.0))
        return round(0.7 * click_norm + 0.3 * open_norm, 4)

    def compare_scores(
        self,
        score_before: float,
        score_after: float,
    ) -> dict[str, Any]:
        """Compare two performance scores and classify the change."""
        absolute_change = score_after - score_before
        if score_before == 0:
            percentage_change = 0.0 if score_after == 0 else 100.0
        else:
            percentage_change = (absolute_change / score_before) * 100

        if percentage_change >= 10:
            significance = "significant"
        elif percentage_change >= 3:
            significance = "moderate"
        else:
            significance = "minimal"

        return {
            "absolute_change": round(absolute_change, 4),
            "percentage_change": round(percentage_change, 2),
            "is_improvement": absolute_change > 0,
            "significance": significance,
        }

    def score_content_quality(
        self,
        subject: str,
        body: str,
        send_time: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Score email content quality based on Mock API optimisation factors.

        Returns scores in [0, 1] for each dimension plus improvement hints.
        """
        opportunities: list[str] = []

        # ── Subject line (40-60 chars ideal) ─────────────────────────────────
        subject_len = len(subject)
        if 40 <= subject_len <= 60:
            subject_score = 1.0
        elif subject_len < 20 or subject_len > 100:
            subject_score = 0.3
            opportunities.append("Subject line length is outside 40-60 character sweet spot")
        else:
            subject_score = 0.6

        urgency_words = {"limited", "expires", "last chance", "urgent", "today", "now", "exclusive"}
        if any(w in subject.lower() for w in urgency_words):
            subject_score = min(1.0, subject_score + 0.2)
        else:
            opportunities.append("Add urgency words to subject (e.g., 'Limited', 'Expires today')")

        if any(tag in subject for tag in ("{name}", "{first_name}", "{{name}}")):
            subject_score = min(1.0, subject_score + 0.1)
        else:
            opportunities.append("Add recipient name personalisation to subject line")

        # ── Body (100-200 words ideal) ────────────────────────────────────────
        word_count = len(body.split())
        if 100 <= word_count <= 200:
            body_score = 1.0
        elif word_count < 50 or word_count > 400:
            body_score = 0.3
            opportunities.append(f"Body word count ({word_count}) is outside 100-200 word ideal range")
        else:
            body_score = 0.6

        cta_phrases = {"click here", "learn more", "buy now", "get started", "shop now", "sign up"}
        if any(p in body.lower() for p in cta_phrases):
            body_score = min(1.0, body_score + 0.2)
        else:
            opportunities.append("Add a clear call-to-action button/link in email body")

        if "<" in body and ">" in body:
            body_score = min(1.0, body_score + 0.1)

        # ── Timing ───────────────────────────────────────────────────────────
        timing_score = 0.5
        if send_time is not None:
            weekday = send_time.weekday()  # 0=Mon, 1=Tue, 2=Wed
            hour = send_time.hour
            if weekday in (1, 2) and 8 <= hour <= 10:
                timing_score = 1.0
            elif weekday in (0, 1, 2, 3) and 7 <= hour <= 12:
                timing_score = 0.7
            else:
                timing_score = 0.3
                opportunities.append("Reschedule to Tuesday/Wednesday 8-10 AM for peak engagement")

        overall = round((subject_score * 0.35 + body_score * 0.40 + timing_score * 0.25), 4)

        return {
            "subject_score": round(subject_score, 4),
            "body_score": round(body_score, 4),
            "timing_score": round(timing_score, 4),
            "overall_score": overall,
            "improvement_opportunities": opportunities,
        }

    # ── Poor performer identification ─────────────────────────────────────────

    async def identify_poor_performers(
        self,
        campaign_id: str,
        percentile: int = 25,
    ) -> list[dict[str, Any]]:
        """Identify the bottom *percentile* % of variants by performance score.

        Requires a minimum sample of 2 variants; returns [] for single-variant campaigns.
        """
        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        if len(metrics_list) < 2:
            return []

        variants = await self.variant_repo.find_by_campaign(campaign_id)
        segment_map = {v.variant_id: v.segment_name for v in variants}

        scored = sorted(
            [
                {
                    "variant_id": m.variant_id,
                    "segment_name": segment_map.get(m.variant_id, ""),
                    "performance_score": m.performance_score,
                    "open_rate": m.open_rate,
                    "click_rate": m.click_rate,
                }
                for m in metrics_list
            ],
            key=lambda x: x["performance_score"],
        )

        avg_score = sum(s["performance_score"] for s in scored) / len(scored)
        cutoff_index = max(1, int(len(scored) * percentile / 100))
        poor = scored[:cutoff_index]

        for p in poor:
            comparison = (
                ((p["performance_score"] - avg_score) / avg_score * 100)
                if avg_score > 0
                else 0.0
            )
            p["comparison_to_avg"] = round(comparison, 2)

        return poor

    # ── Segment performance ───────────────────────────────────────────────────

    async def analyze_segment_performance(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Aggregate performance scores per segment for a campaign."""
        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        variants = await self.variant_repo.find_by_campaign(campaign_id)
        segment_map = {v.variant_id: v.segment_name for v in variants}

        segment_scores: dict[str, list[float]] = {}
        for m in metrics_list:
            seg = segment_map.get(m.variant_id, "unknown")
            segment_scores.setdefault(seg, []).append(m.performance_score)

        summaries = [
            {
                "segment_name": seg,
                "avg_score": round(sum(scores) / len(scores), 4),
                "variant_count": len(scores),
            }
            for seg, scores in segment_scores.items()
        ]
        summaries.sort(key=lambda x: x["avg_score"], reverse=True)

        return {
            "segment_performance": summaries,
            "best_segment": summaries[0]["segment_name"] if summaries else None,
            "worst_segment": summaries[-1]["segment_name"] if summaries else None,
        }
