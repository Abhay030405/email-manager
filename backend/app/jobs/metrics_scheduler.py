"""Periodic metrics collection scheduler — collects metrics for active campaigns."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MetricsScheduler:
    """Schedules periodic metrics collection using a plain asyncio loop.

    No external library required.  Call ``start()`` once at application startup
    and ``stop()`` during shutdown.
    """

    def __init__(
        self,
        metrics_collection_service: Any,
        interval_seconds: int = 300,
    ) -> None:
        self._svc = metrics_collection_service
        self._interval = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        """Start the background scheduler task."""
        if self._task and not self._task.done():
            logger.warning("MetricsScheduler already running")
            return
        self._running = True
        self._task = asyncio.ensure_future(self._loop())
        logger.info("MetricsScheduler started (interval=%ds)", self._interval)

    def stop(self) -> None:
        """Stop the background scheduler task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("MetricsScheduler stopped")

    async def run_once(self) -> dict:
        """Manually trigger one collection cycle (useful for testing)."""
        return await self.job_collect_active_campaigns_metrics()

    async def job_collect_active_campaigns_metrics(self) -> dict:
        """Collect metrics for all active campaigns."""
        logger.info("MetricsScheduler: collecting active campaign metrics")
        try:
            result = await self._svc.collect_all_active_campaigns_metrics()
            logger.info(
                "MetricsScheduler: collected %d campaigns (%d variants)",
                result.get("total_campaigns", 0),
                result.get("total_variants", 0),
            )
            return result
        except Exception as exc:
            logger.error("MetricsScheduler: collection job failed: %s", exc)
            return {"error": str(exc)}

    async def _loop(self) -> None:
        while self._running:
            await self.job_collect_active_campaigns_metrics()
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
