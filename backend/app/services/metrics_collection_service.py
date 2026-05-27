"""Metrics collection service — fetches and caches campaign metrics from the Mock API."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Optional

from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.variant_repo import VariantRepository
from app.external.mock_campaign_client import MockCampaignClient, MockCampaignAPIError
from app.models.metrics import Metrics
from app.utils.metrics_utils import (
    calculate_engagement_score,
    calculate_performance_score,
    convert_mock_api_metrics_to_percentages,
)

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_TTL_MINUTES = 5


class MetricsCollectionService:
    """Fetches campaign metrics from the Mock API with caching and error recovery."""

    def __init__(
        self,
        mock_api_client: MockCampaignClient,
        metrics_repo: MetricsRepository,
        campaign_repo: CampaignRepository,
        variant_repo: VariantRepository,
        cache_ttl_minutes: int = _DEFAULT_CACHE_TTL_MINUTES,
    ) -> None:
        self.mock_api_client = mock_api_client
        self.metrics_repo = metrics_repo
        self.campaign_repo = campaign_repo
        self.variant_repo = variant_repo
        self.cache_ttl_minutes = cache_ttl_minutes

    # ── Public API ─────────────────────────────────────────────────────────────

    async def collect_campaign_metrics(
        self,
        campaign_id: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Collect metrics from the Mock API for all variants of a campaign.

        Returns a summary dict with collected metrics and timing information.
        """
        t0 = time.monotonic()
        campaign = await self.campaign_repo.find_by_id(campaign_id)
        if not campaign:
            return {"campaign_id": campaign_id, "error": "Campaign not found", "variants_collected": 0}

        mock_ids: dict[str, str] = {}
        if campaign.mock_campaign_id:
            # Single-variant campaigns store mock_campaign_id on the campaign
            mock_ids["default"] = campaign.mock_campaign_id

        # Also get per-variant mappings from VariantRepository
        variants = await self.variant_repo.find_by_campaign(campaign_id)
        for v in variants:
            if getattr(v, "mock_campaign_id", None):
                mock_ids[v.variant_id] = v.mock_campaign_id

        if not mock_ids:
            logger.info("No mock_campaign_ids for campaign %s — skipping collection", campaign_id)
            return {
                "campaign_id": campaign_id,
                "variants_collected": 0,
                "total_metrics": [],
                "source": "skipped",
                "collected_at": datetime.now(tz=timezone.utc).isoformat(),
                "duration_seconds": round(time.monotonic() - t0, 3),
            }

        collected: list[dict[str, Any]] = []
        source = "mock_api"

        for variant_id, mock_campaign_id in mock_ids.items():
            cached = None if force_refresh else await self.get_cached_metrics(campaign_id, variant_id)
            if cached:
                collected.append(cached.model_dump())
                source = "cached"
                continue

            try:
                raw = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda mid=mock_campaign_id: self.mock_api_client.get_campaign_metrics(mid),
                )
                metrics = await self._build_and_save_metrics(campaign_id, variant_id, mock_campaign_id, raw)
                collected.append(metrics.model_dump())
            except Exception as exc:
                logger.error("Metrics collection failed for variant %s: %s", variant_id, exc)
                await self.handle_collection_error(exc, campaign_id, f"variant={variant_id}")

        return {
            "campaign_id": campaign_id,
            "variants_collected": len(collected),
            "total_metrics": collected,
            "collected_at": datetime.now(tz=timezone.utc).isoformat(),
            "source": source,
            "duration_seconds": round(time.monotonic() - t0, 3),
        }

    async def collect_all_active_campaigns_metrics(self) -> dict[str, Any]:
        """Collect metrics for all campaigns with EXECUTING or COMPLETED status."""
        t0 = time.monotonic()
        from app.models.campaign import CampaignStatus

        campaigns = await self.campaign_repo.find_all(
            filter={"status": {"$in": [CampaignStatus.EXECUTING.value, CampaignStatus.COMPLETED.value]}}
        )

        results: list[dict[str, Any]] = []
        errors: list[str] = []
        total_variants = 0

        for campaign in campaigns:
            try:
                result = await self.collect_campaign_metrics(campaign.campaign_id)
                total_variants += result.get("variants_collected", 0)
                results.append(result)
            except Exception as exc:
                errors.append(f"{campaign.campaign_id}: {exc}")
                logger.error("Batch collection failed for %s: %s", campaign.campaign_id, exc)

        return {
            "total_campaigns": len(campaigns),
            "successful": len(results),
            "failed": len(errors),
            "total_variants": total_variants,
            "duration_seconds": round(time.monotonic() - t0, 3),
            "errors": errors,
        }

    async def collect_customer_results(
        self,
        campaign_id: str,
        variant_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Fetch per-customer open/click results from the Mock API."""
        variants = await self.variant_repo.find_by_campaign(campaign_id)
        results: list[dict[str, Any]] = []

        for v in variants:
            if variant_id and v.variant_id != variant_id:
                continue
            mid = getattr(v, "mock_campaign_id", None)
            if not mid:
                continue
            try:
                customer_data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda m=mid: self.mock_api_client.get_campaign_results(m, limit=500),
                )
                for row in customer_data:
                    row["variant_id"] = v.variant_id
                results.extend(customer_data)
            except Exception as exc:
                logger.warning("Customer results fetch failed for variant %s: %s", v.variant_id, exc)

        return results

    async def stream_metrics_updates(
        self,
        campaign_id: str,
        interval_seconds: int = 60,
        max_duration_minutes: int = 1440,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Async generator that yields fresh metrics at *interval_seconds* intervals."""
        start = time.monotonic()
        max_seconds = max_duration_minutes * 60
        while True:
            metrics = await self.collect_campaign_metrics(campaign_id, force_refresh=True)
            yield metrics
            elapsed = time.monotonic() - start
            if elapsed >= max_seconds:
                break
            await asyncio.sleep(interval_seconds)

    async def validate_metrics_integrity(
        self, metrics: Metrics
    ) -> tuple[bool, list[str]]:
        """Validate that metrics values are internally consistent."""
        errors: list[str] = []
        for field in ("open_rate", "click_rate", "click_through_rate"):
            val = getattr(metrics, field, None)
            if val is not None and not (0.0 <= val <= 1.0):
                errors.append(f"{field} out of range [0, 1]: {val}")
        if metrics.unique_clicks > metrics.unique_opens and metrics.unique_opens > 0:
            errors.append(
                f"unique_clicks ({metrics.unique_clicks}) > unique_opens ({metrics.unique_opens})"
            )
        if metrics.unique_opens > metrics.total_sent and metrics.total_sent > 0:
            errors.append(
                f"unique_opens ({metrics.unique_opens}) > total_sent ({metrics.total_sent})"
            )
        return len(errors) == 0, errors

    async def get_cached_metrics(
        self,
        campaign_id: str,
        variant_id: str,
        max_age_minutes: int | None = None,
    ) -> Optional[Metrics]:
        """Return cached metrics if still within TTL, else None."""
        ttl = max_age_minutes if max_age_minutes is not None else self.cache_ttl_minutes
        cached = await self.metrics_repo.get_latest_by_variant(campaign_id, variant_id)
        if cached is None:
            return None
        ts = cached.collected_at or cached.calculated_at
        if ts and (datetime.utcnow() - ts) < timedelta(minutes=ttl):
            return cached
        return None

    async def handle_collection_error(
        self, error: Exception, campaign_id: str, context: str
    ) -> None:
        """Log and classify a collection error; fall back to last known metrics."""
        if isinstance(error, MockCampaignAPIError):
            if error.status_code == 404:
                logger.warning("Campaign %s not found in Mock API (%s)", campaign_id, context)
            else:
                logger.error("Mock API %d error for %s (%s): %s", error.status_code, campaign_id, context, error.detail)
        else:
            logger.error("Unexpected collection error for %s (%s): %s", campaign_id, context, error)

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _build_and_save_metrics(
        self,
        campaign_id: str,
        variant_id: str,
        mock_campaign_id: str,
        raw: dict[str, Any],
    ) -> Metrics:
        """Convert raw Mock API response to a Metrics model and persist it."""
        open_rate_raw = float(raw.get("open_rate", 0.0))
        click_rate_raw = float(raw.get("click_rate", 0.0))
        ctr_raw = float(raw.get("click_through_rate", 0.0))

        perf_score = calculate_performance_score(open_rate_raw * 100, click_rate_raw * 100)
        engagement = calculate_engagement_score(open_rate_raw * 100, click_rate_raw * 100, ctr_raw * 100)

        metrics = Metrics(
            variant_id=variant_id,
            campaign_id=campaign_id,
            mock_campaign_id=mock_campaign_id,
            total_sent=int(raw.get("total_sent", 0)),
            unique_opens=int(raw.get("unique_opens", 0)),
            unique_clicks=int(raw.get("unique_clicks", 0)),
            open_rate=open_rate_raw,
            click_rate=click_rate_raw,
            click_through_rate=ctr_raw,
            performance_score=perf_score,
            collected_at=datetime.utcnow(),
        )
        await self.metrics_repo.upsert(metrics)
        return metrics
