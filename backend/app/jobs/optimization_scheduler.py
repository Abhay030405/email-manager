"""Optimization scheduler — asyncio-based periodic optimization trigger."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OptimizationScheduler:
    """Periodically checks active campaigns and triggers optimization if warranted."""

    def __init__(
        self,
        optimization_service: Any,
        campaign_repo: Any,
        check_interval_hours: int = 4,
    ) -> None:
        self.optimization_service = optimization_service
        self.campaign_repo = campaign_repo
        self.check_interval_hours = check_interval_hours
        self._task: Optional[asyncio.Task] = None
        self._stats: dict[str, Any] = {
            "campaigns_checked": 0,
            "optimizations_triggered": 0,
            "errors": 0,
            "start_time": time.monotonic(),
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start_optimization_checks(self, interval_hours: Optional[int] = None) -> asyncio.Task:
        """Start the periodic optimization check loop."""
        hours = interval_hours or self.check_interval_hours
        self._task = asyncio.ensure_future(self._run_loop(hours))
        logger.info("OptimizationScheduler started (interval=%dh)", hours)
        return self._task

    async def stop(self) -> None:
        """Cancel the running loop gracefully."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("OptimizationScheduler stopped")

    async def run_once(self) -> dict[str, Any]:
        """Execute a single optimization check cycle immediately."""
        return await self.job_trigger_optimization_if_needed()

    def get_stats(self) -> dict[str, Any]:
        uptime = time.monotonic() - self._stats["start_time"]
        return {**self._stats, "uptime_seconds": round(uptime, 1)}

    # ── Job ───────────────────────────────────────────────────────────────────

    async def job_trigger_optimization_if_needed(self) -> dict[str, Any]:
        """Check all executing/completed campaigns and trigger optimization if needed."""
        from app.models.campaign import CampaignStatus

        triggered: list[str] = []
        errors: list[str] = []

        try:
            campaigns = await self.campaign_repo.find_all(
                filter={
                    "status": {
                        "$in": [
                            CampaignStatus.EXECUTING.value,
                            CampaignStatus.COMPLETED.value,
                            CampaignStatus.OPTIMIZING.value,
                        ]
                    }
                }
            )
        except Exception as exc:
            logger.error("Failed to fetch campaigns: %s", exc)
            return {"triggered": [], "errors": [str(exc)]}

        for campaign in campaigns:
            self._stats["campaigns_checked"] += 1
            try:
                result = await self.optimization_service.execute_full_optimization_workflow(
                    campaign_id=campaign.campaign_id,
                    max_iterations=1,
                    enable_ab_testing=False,
                )
                if result.get("variants_improved", 0) > 0:
                    triggered.append(campaign.campaign_id)
                    self._stats["optimizations_triggered"] += 1
                    logger.info("Optimization triggered for campaign %s", campaign.campaign_id)
            except Exception as exc:
                errors.append(f"{campaign.campaign_id}: {exc}")
                self._stats["errors"] += 1
                logger.error("Optimization failed for campaign %s: %s", campaign.campaign_id, exc)

        logger.info(
            "OptimizationScheduler cycle done: %d triggered, %d errors",
            len(triggered), len(errors),
        )
        return {"triggered": triggered, "errors": errors}

    # ── Private ───────────────────────────────────────────────────────────────

    async def _run_loop(self, interval_hours: int) -> None:
        interval_seconds = interval_hours * 3600
        while True:
            try:
                await self.job_trigger_optimization_if_needed()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Scheduler loop error: %s", exc)
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
