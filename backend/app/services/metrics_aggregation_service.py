"""Metrics aggregation service — rolls up metrics across variants, segments, and time."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.metric_aggregation_repo import MetricAggregationRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.variant_repo import VariantRepository
from app.models.metric_aggregation import MetricAggregation
from app.utils.metrics_utils import calculate_std_dev

logger = logging.getLogger(__name__)


class MetricsAggregationService:
    """Aggregates metrics across campaigns, segments, and variants."""

    def __init__(
        self,
        metrics_repo: MetricsRepository,
        aggregation_repo: MetricAggregationRepository,
        variant_repo: VariantRepository,
        campaign_repo: CampaignRepository,
    ) -> None:
        self.metrics_repo = metrics_repo
        self.aggregation_repo = aggregation_repo
        self.variant_repo = variant_repo
        self.campaign_repo = campaign_repo

    async def aggregate_campaign_metrics(self, campaign_id: str) -> MetricAggregation:
        """Aggregate metrics across all variants of a campaign."""
        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        return await self._build_and_store(
            campaign_id=campaign_id,
            aggregation_type="campaign_total",
            aggregation_key=campaign_id,
            metrics_list=[m.model_dump() for m in metrics_list],
        )

    async def aggregate_segment_metrics(
        self, campaign_id: str, segment_name: str
    ) -> MetricAggregation:
        """Aggregate metrics for a named segment within a campaign."""
        variants = await self.variant_repo.find_by_campaign(campaign_id)
        seg_variant_ids = {v.variant_id for v in variants if v.segment_name == segment_name}

        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        seg_metrics = [m.model_dump() for m in metrics_list if m.variant_id in seg_variant_ids]
        return await self._build_and_store(
            campaign_id=campaign_id,
            aggregation_type="segment",
            aggregation_key=segment_name,
            metrics_list=seg_metrics,
        )

    async def aggregate_variant_metrics(
        self, campaign_id: str, variant_id: str
    ) -> MetricAggregation:
        """Aggregate all historical metrics for a single variant."""
        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        v_metrics = [m.model_dump() for m in metrics_list if m.variant_id == variant_id]
        return await self._build_and_store(
            campaign_id=campaign_id,
            aggregation_type="variant",
            aggregation_key=variant_id,
            metrics_list=v_metrics,
        )

    async def aggregate_metrics_by_period(
        self,
        campaign_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> MetricAggregation:
        """Aggregate metrics within a specific time window."""
        metrics_list = await self.metrics_repo.get_metrics_time_series(
            campaign_id, period_start, period_end
        )
        key = period_start.strftime("%Y-%m-%d")
        agg = await self._build_and_store(
            campaign_id=campaign_id,
            aggregation_type="temporal",
            aggregation_key=key,
            metrics_list=[m.model_dump() for m in metrics_list],
        )
        agg.period_start = period_start
        agg.period_end = period_end
        return agg

    async def compare_variants(self, campaign_id: str) -> dict[str, Any]:
        """Rank all variants by performance_score and return comparison dict."""
        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        if not metrics_list:
            return {"best_variant": None, "worst_variant": None, "variance": 0.0, "recommendation": "No data"}

        ranked = sorted(metrics_list, key=lambda m: m.performance_score, reverse=True)
        scores = [m.performance_score for m in ranked]

        return {
            "best_variant": _metrics_summary(ranked[0]),
            "worst_variant": _metrics_summary(ranked[-1]),
            "all_variants": [_metrics_summary(m) for m in ranked],
            "variance": round(calculate_std_dev(scores) ** 2, 6),
            "recommendation": _variant_recommendation(ranked[0], ranked[-1]),
        }

    async def compare_segments(self, campaign_id: str) -> dict[str, Any]:
        """Rank all segments by average open rate."""
        variants = await self.variant_repo.find_by_campaign(campaign_id)
        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        metrics_by_variant = {m.variant_id: m for m in metrics_list}

        segment_data: dict[str, list[float]] = {}
        for v in variants:
            m = metrics_by_variant.get(v.variant_id)
            if m:
                segment_data.setdefault(v.segment_name, []).append(m.open_rate)

        if not segment_data:
            return {"segments": [], "best_segment": None, "worst_segment": None}

        summaries = [
            {"segment_name": seg, "avg_open_rate": round(sum(rates) / len(rates), 4)}
            for seg, rates in segment_data.items()
        ]
        summaries.sort(key=lambda s: s["avg_open_rate"], reverse=True)
        return {
            "segments": summaries,
            "best_segment": summaries[0] if summaries else None,
            "worst_segment": summaries[-1] if summaries else None,
        }

    # ── Private ────────────────────────────────────────────────────────────────

    async def _build_and_store(
        self,
        campaign_id: str,
        aggregation_type: str,
        aggregation_key: str,
        metrics_list: list[dict[str, Any]],
    ) -> MetricAggregation:
        if not metrics_list:
            agg = MetricAggregation(
                aggregation_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                aggregation_type=aggregation_type,
                aggregation_key=aggregation_key,
                data_point_count=0,
            )
        else:
            total_sent = sum(m.get("total_sent", 0) for m in metrics_list)
            total_opens = sum(m.get("unique_opens", 0) for m in metrics_list)
            total_clicks = sum(m.get("unique_clicks", 0) for m in metrics_list)
            open_rates = [m.get("open_rate", 0.0) for m in metrics_list]
            click_rates = [m.get("click_rate", 0.0) for m in metrics_list]

            agg_open = (total_opens / total_sent * 100) if total_sent else 0.0
            agg_click = (total_clicks / total_sent * 100) if total_sent else 0.0
            agg_ctr = (total_clicks / total_opens * 100) if total_opens else 0.0

            agg = MetricAggregation(
                aggregation_id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                aggregation_type=aggregation_type,
                aggregation_key=aggregation_key,
                total_sent=total_sent,
                total_opens=total_opens,
                total_clicks=total_clicks,
                open_rate=round(agg_open, 4),
                click_rate=round(agg_click, 4),
                ctr=round(agg_ctr, 4),
                std_dev_open_rate=calculate_std_dev([r * 100 for r in open_rates]),
                std_dev_click_rate=calculate_std_dev([r * 100 for r in click_rates]),
                data_point_count=len(metrics_list),
                created_at=datetime.now(tz=timezone.utc),
                last_updated=datetime.now(tz=timezone.utc),
            )

        data = agg.model_dump()
        return await self.aggregation_repo.upsert_for_campaign(
            campaign_id, aggregation_type, aggregation_key, data
        )


def _metrics_summary(m: Any) -> dict[str, Any]:
    return {
        "variant_id": m.variant_id,
        "open_rate": m.open_rate,
        "click_rate": m.click_rate,
        "performance_score": m.performance_score,
    }


def _variant_recommendation(best: Any, worst: Any) -> str:
    delta = best.performance_score - worst.performance_score
    if delta > 0.2:
        return f"Variant {best.variant_id} significantly outperforms {worst.variant_id}. Consider scaling the winner."
    if delta > 0.05:
        return f"Variant {best.variant_id} edges out {worst.variant_id}. Monitor for statistical significance."
    return "Variant performance is similar. Collect more data before making changes."
