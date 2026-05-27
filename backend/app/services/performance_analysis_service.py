"""Performance analysis service — trends, predictions, and segment breakdowns."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.db.repositories.analytics_repo import AnalyticsRepository
from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.customer_repo import CustomerRepository
from app.db.repositories.metric_aggregation_repo import MetricAggregationRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.utils.metrics_utils import calculate_percentile, calculate_trend

logger = logging.getLogger(__name__)


class PerformanceAnalysisService:
    """Derives insights, trends, predictions, and comparisons from stored metrics."""

    def __init__(
        self,
        metrics_repo: MetricsRepository,
        analytics_repo: AnalyticsRepository,
        aggregation_repo: MetricAggregationRepository,
        customer_repo: CustomerRepository,
        campaign_repo: CampaignRepository,
    ) -> None:
        self.metrics_repo = metrics_repo
        self.analytics_repo = analytics_repo
        self.aggregation_repo = aggregation_repo
        self.customer_repo = customer_repo
        self.campaign_repo = campaign_repo

    # ── Public API ─────────────────────────────────────────────────────────────

    async def analyze_campaign_performance(self, campaign_id: str) -> dict[str, Any]:
        """Comprehensive performance analysis for a campaign."""
        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        if not metrics_list:
            return {
                "campaign_id": campaign_id,
                "overall_metrics": {},
                "trends": {},
                "variant_analysis": [],
                "segment_analysis": [],
                "recommendations": ["No metrics data available yet."],
                "analysis_timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }

        # Overall aggregates
        total_sent = sum(m.total_sent for m in metrics_list)
        total_opens = sum(m.unique_opens for m in metrics_list)
        total_clicks = sum(m.unique_clicks for m in metrics_list)
        avg_open = (total_opens / total_sent * 100) if total_sent else 0.0
        avg_click = (total_clicks / total_sent * 100) if total_sent else 0.0
        avg_ctr = (total_clicks / total_opens * 100) if total_opens else 0.0

        open_trend_dir, open_rate_change = calculate_trend([m.open_rate for m in metrics_list])
        click_trend_dir, click_rate_change = calculate_trend([m.click_rate for m in metrics_list])

        variant_analysis = sorted(
            [
                {
                    "variant_id": m.variant_id,
                    "open_rate": round(m.open_rate * 100, 2),
                    "click_rate": round(m.click_rate * 100, 2),
                    "performance_score": m.performance_score,
                    "total_sent": m.total_sent,
                }
                for m in metrics_list
            ],
            key=lambda x: x["performance_score"],
            reverse=True,
        )

        recommendations = _build_recommendations(avg_open, avg_click, open_trend_dir, click_trend_dir)

        snapshot = AnalyticsSnapshot(
            campaign_id=campaign_id,
            total_sent=total_sent,
            total_opens=total_opens,
            total_clicks=total_clicks,
            open_rate=round(avg_open, 4),
            click_rate=round(avg_click, 4),
            ctr=round(avg_ctr, 4),
            open_rate_trend=open_trend_dir,
            click_rate_trend=click_trend_dir,
            best_performing_variant=variant_analysis[0] if variant_analysis else {},
            worst_performing_variant=variant_analysis[-1] if len(variant_analysis) > 1 else {},
        )
        try:
            await self.analytics_repo.create_snapshot(snapshot)
        except Exception as exc:
            logger.warning("Failed to persist analytics snapshot: %s", exc)

        return {
            "campaign_id": campaign_id,
            "overall_metrics": {
                "total_sent": total_sent,
                "total_opens": total_opens,
                "total_clicks": total_clicks,
                "open_rate": round(avg_open, 2),
                "click_rate": round(avg_click, 2),
                "ctr": round(avg_ctr, 2),
            },
            "trends": {
                "open_rate": open_trend_dir,
                "open_rate_change_pct": open_rate_change,
                "click_rate": click_trend_dir,
                "click_rate_change_pct": click_rate_change,
            },
            "variant_analysis": variant_analysis,
            "segment_analysis": [],
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    async def calculate_trend(
        self,
        campaign_id: str,
        metric_name: str,
        lookback_hours: int = 24,
    ) -> dict[str, Any]:
        """Calculate trend for a specific metric over the last N hours."""
        trend_dir = await self.metrics_repo.calculate_trend(
            campaign_id, metric_name, window_hours=lookback_hours
        )
        history = await self.metrics_repo.get_metrics_history(campaign_id, days=max(1, lookback_hours // 24))
        values = [getattr(m, metric_name, 0.0) or 0.0 for m in history]
        _, rate = calculate_trend(values)
        projected = (values[-1] * (1 + rate / 100)) if values else 0.0
        confidence = min(1.0, len(values) / 10)
        return {
            "trend": trend_dir,
            "rate_of_change": rate,
            "projected_value": round(projected, 4),
            "confidence": round(confidence, 2),
            "data_points": len(values),
        }

    async def analyze_segment_performance(
        self, campaign_id: str, segment_name: str
    ) -> dict[str, Any]:
        """Analyse metrics for a named segment."""
        from app.db.repositories.variant_repo import VariantRepository
        from app.db.mongodb import MongoDB
        variant_repo = VariantRepository(self.metrics_repo.db)
        variants = await variant_repo.find_by_campaign(campaign_id)
        seg_ids = {v.variant_id for v in variants if v.segment_name == segment_name}
        seg_customers = sum(len(v.customer_ids) for v in variants if v.variant_id in seg_ids)

        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        seg_metrics = [m for m in metrics_list if m.variant_id in seg_ids]

        if not seg_metrics:
            return {"segment_name": segment_name, "total_customers": seg_customers, "open_rate": 0.0, "click_rate": 0.0, "improvement_potential": 0.0, "recommendations": ["No metrics for this segment."]}

        avg_open = sum(m.open_rate for m in seg_metrics) / len(seg_metrics) * 100
        avg_click = sum(m.click_rate for m in seg_metrics) / len(seg_metrics) * 100

        return {
            "segment_name": segment_name,
            "total_customers": seg_customers,
            "open_rate": round(avg_open, 2),
            "click_rate": round(avg_click, 2),
            "engagement_factors": {"variants_in_segment": len(seg_metrics)},
            "improvement_potential": round(max(0.0, 30.0 - avg_open), 2),
            "recommendations": _build_recommendations(avg_open, avg_click, "stable", "stable"),
        }

    async def analyze_time_to_metrics(self, campaign_id: str) -> dict[str, Any]:
        """Placeholder for time-to-metrics analysis (requires event-level data)."""
        return {
            "campaign_id": campaign_id,
            "time_to_first_open_minutes": 0,
            "time_to_first_click_minutes": 0,
            "median_open_time": 0,
            "median_click_time": 0,
            "distribution": {"note": "Requires event-level timestamps not yet available"},
        }

    async def predict_final_metrics(
        self, campaign_id: str, based_on_hours: int = 24
    ) -> dict[str, Any]:
        """Project final metrics based on early performance using simple linear extrapolation."""
        history = await self.metrics_repo.get_metrics_history(campaign_id, days=max(1, based_on_hours // 24))
        if not history:
            return {"projected_open_rate": 0.0, "projected_click_rate": 0.0, "confidence_interval": (0.0, 0.0), "estimate_reliability": 0.0}

        open_vals = [m.open_rate * 100 for m in history]
        click_vals = [m.click_rate * 100 for m in history]
        _, open_rate = calculate_trend(open_vals)
        _, click_rate = calculate_trend(click_vals)

        proj_open = max(0.0, min(100.0, open_vals[-1] * (1 + open_rate / 100)))
        proj_click = max(0.0, min(100.0, click_vals[-1] * (1 + click_rate / 100)))
        reliability = min(1.0, len(history) / 5)

        from app.utils.metrics_utils import calculate_std_dev
        std = calculate_std_dev(open_vals) or 5.0
        return {
            "projected_open_rate": round(proj_open, 2),
            "projected_click_rate": round(proj_click, 2),
            "confidence_interval": (round(max(0, proj_open - std), 2), round(min(100, proj_open + std), 2)),
            "estimate_reliability": round(reliability, 2),
        }

    async def compare_to_baseline(self, campaign_id: str) -> dict[str, Any]:
        """Compare current campaign to the average of all other completed campaigns."""
        from app.models.campaign import CampaignStatus

        all_campaigns = await self.campaign_repo.find_all(
            filter={"status": CampaignStatus.COMPLETED.value, "campaign_id": {"$ne": campaign_id}}
        )
        baseline_open_rates: list[float] = []
        for c in all_campaigns:
            agg = await self.metrics_repo.calculate_campaign_aggregates(c.campaign_id)
            if agg.get("avg_open_rate"):
                baseline_open_rates.append(agg["avg_open_rate"] * 100)

        current_agg = await self.metrics_repo.calculate_campaign_aggregates(campaign_id)
        current_open = (current_agg.get("avg_open_rate") or 0.0) * 100

        if not baseline_open_rates:
            return {
                "baseline_open_rate": None,
                "current_open_rate": round(current_open, 2),
                "variance_percentage": None,
                "percentile": None,
                "status": "no_baseline",
            }

        baseline = sum(baseline_open_rates) / len(baseline_open_rates)
        variance = ((current_open - baseline) / baseline * 100) if baseline else 0.0
        pct = calculate_percentile(current_open, baseline_open_rates)
        status = "above_average" if current_open >= baseline else "below_average"

        return {
            "baseline_open_rate": round(baseline, 2),
            "current_open_rate": round(current_open, 2),
            "variance_percentage": round(variance, 2),
            "percentile": pct,
            "status": status,
        }


def _build_recommendations(
    open_rate: float, click_rate: float, open_trend: str, click_trend: str
) -> list[str]:
    recs: list[str] = []
    if open_rate < 15:
        recs.append("Open rate critically low. Revisit subject line and send time.")
    elif open_rate < 30:
        recs.append("Open rate below benchmark. Try A/B testing subject lines.")
    if click_rate < 1:
        recs.append("Click rate very low. Ensure the CTA is prominent and link is correct.")
    elif click_rate < 5:
        recs.append("Click rate below benchmark. Personalise body copy and CTA text.")
    if open_trend == "declining":
        recs.append("Open rate trending down. Investigate audience fatigue or deliverability issues.")
    if click_trend == "declining":
        recs.append("Click rate trending down. Refresh email content and re-evaluate segments.")
    if not recs:
        recs.append("Performance is on track. Continue monitoring for sustained engagement.")
    return recs
