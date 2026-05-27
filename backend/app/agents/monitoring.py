"""Performance Monitoring Agent — fetches campaign metrics from the Mock Campaign API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import BaseAgent
from app.db.mongodb import MongoDB
from app.db.repositories.metrics_repo import MetricsRepository
from app.external.mock_campaign_client import MockCampaignClient, MockCampaignAPIError
from app.models.metrics import Metrics

logger = logging.getLogger(__name__)


class MonitoringAgent(BaseAgent):
    """Fetches aggregated metrics and per-customer results from the Mock Campaign API.

    For each mock_api_campaign_id:
    1. Calls GET /api/campaigns/{id}/metrics for aggregated stats.
    2. Validates the metrics response fields.
    3. Calls GET /api/campaigns/{id}/results for per-customer outcomes.
    4. Persists metrics to MongoDB.
    5. Caches aggregated results in-memory to avoid redundant API calls.
    """

    def __init__(self) -> None:
        super().__init__(model_name="gpt-4", temperature=0.0, max_tokens=512)
        self._client = MockCampaignClient()
        # campaign_id → aggregated result cache
        self._cache: dict[str, dict[str, Any]] = {}

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        campaign_id = input_data.get("campaign_id", "")
        mock_api_campaign_ids = input_data.get("mock_api_campaign_ids", {})
        return await self.collect_metrics(campaign_id, mock_api_campaign_ids)

    def invalidate_cache(self, campaign_id: str) -> None:
        """Remove cached metrics for a campaign so the next call re-fetches."""
        self._cache.pop(campaign_id, None)

    async def collect_metrics(
        self,
        campaign_id: str,
        mock_api_campaign_ids: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Collect performance metrics for all variants of a campaign.

        Returns cached result if already collected during this session.

        Returns:
            Dict with ``variant_metrics``, ``aggregates``, and ``customer_results``.
        """
        self._log_action("collect_metrics", {
            "campaign_id": campaign_id,
            "variant_count": len(mock_api_campaign_ids or {}),
        })

        if not mock_api_campaign_ids:
            return await self._load_metrics_from_db(campaign_id)

        if campaign_id in self._cache:
            logger.info("Returning cached metrics for campaign %s", campaign_id)
            return self._cache[campaign_id]

        variant_metrics: list[dict[str, Any]] = []
        customer_results: list[dict[str, Any]] = []
        repo = MetricsRepository(MongoDB.get_db())

        for variant_id, mock_campaign_id in (mock_api_campaign_ids or {}).items():
            try:
                raw = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda mid=mock_campaign_id: self._client.get_campaign_metrics(mid),
                )

                # Validate the response shape
                try:
                    self._client._validate_metrics_response(raw)
                except ValueError as exc:
                    logger.warning("Metrics response validation failed for %s: %s", mock_campaign_id, exc)

                # Mock API returns rates as 0.0–1.0; convert to percentages for state
                open_rate_raw = float(raw.get("open_rate", 0.0))
                click_rate_raw = float(raw.get("click_rate", 0.0))
                ctr_raw = float(raw.get("click_through_rate", 0.0))

                metric_entry: dict[str, Any] = {
                    "variant_id": variant_id,
                    "mock_campaign_id": mock_campaign_id,
                    "total_sent": int(raw.get("total_sent", 0)),
                    "unique_opens": int(raw.get("unique_opens", 0)),
                    "unique_clicks": int(raw.get("unique_clicks", 0)),
                    "open_rate": open_rate_raw * 100,
                    "click_rate": click_rate_raw * 100,
                    "click_through_rate": ctr_raw * 100,
                    "collected_at": datetime.now(tz=timezone.utc).isoformat(),
                }
                variant_metrics.append(metric_entry)

                # Persist to MongoDB using raw 0.0-1.0 values
                try:
                    metrics_model = Metrics(
                        variant_id=variant_id,
                        campaign_id=campaign_id,
                        mock_campaign_id=mock_campaign_id,
                        total_sent=metric_entry["total_sent"],
                        unique_opens=metric_entry["unique_opens"],
                        unique_clicks=metric_entry["unique_clicks"],
                        open_rate=open_rate_raw,
                        click_rate=click_rate_raw,
                        click_through_rate=ctr_raw,
                    )
                    await repo.upsert(metrics_model)
                except Exception as db_exc:
                    logger.warning("Failed to persist metrics for %s: %s", variant_id, db_exc)

            except MockCampaignAPIError as exc:
                logger.error("Metrics fetch failed for %s: %s", mock_campaign_id, exc)
                variant_metrics.append({
                    "variant_id": variant_id,
                    "mock_campaign_id": mock_campaign_id,
                    "error": exc.detail,
                    "open_rate": 0.0,
                    "click_rate": 0.0,
                    "click_through_rate": 0.0,
                })
            except Exception as exc:
                logger.error("Unexpected metrics error for %s: %s", mock_campaign_id, exc)

            # Per-customer results
            try:
                results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda mid=mock_campaign_id: self._client.get_campaign_results(mid, limit=500),
                )
                for r in results:
                    r["variant_id"] = variant_id
                customer_results.extend(results)
            except Exception as exc:
                logger.warning("Per-customer results fetch failed for %s: %s", mock_campaign_id, exc)

        aggregates = _compute_aggregates(variant_metrics)
        result = {
            "variant_metrics": variant_metrics,
            "aggregates": aggregates,
            "customer_results": customer_results,
        }
        self._cache[campaign_id] = result
        return result

    async def _load_metrics_from_db(self, campaign_id: str) -> dict[str, Any]:
        repo = MetricsRepository(MongoDB.get_db())
        metric_docs = await repo.find_by_campaign(campaign_id)
        aggregates = await repo.calculate_campaign_aggregates(campaign_id)
        return {
            "variant_metrics": [doc.model_dump() for doc in metric_docs],
            "aggregates": aggregates,
            "customer_results": [],
        }


def _compute_aggregates(variant_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [m for m in variant_metrics if "error" not in m]
    if not valid:
        return {}
    total_sent = sum(m.get("total_sent", 0) for m in valid)
    total_opens = sum(m.get("unique_opens", 0) for m in valid)
    total_clicks = sum(m.get("unique_clicks", 0) for m in valid)
    return {
        "avg_open_rate": round(sum(m["open_rate"] for m in valid) / len(valid), 4),
        "avg_click_rate": round(sum(m["click_rate"] for m in valid) / len(valid), 4),
        "avg_ctr": round(sum(m["click_through_rate"] for m in valid) / len(valid), 4),
        "total_sent": total_sent,
        "total_opens": total_opens,
        "total_clicks": total_clicks,
        "overall_open_rate": round(total_opens / total_sent * 100, 4) if total_sent else 0.0,
        "overall_click_rate": round(total_clicks / total_sent * 100, 4) if total_sent else 0.0,
    }
