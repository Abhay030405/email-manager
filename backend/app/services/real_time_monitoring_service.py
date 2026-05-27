"""Real-time monitoring service — manages per-campaign monitoring loops."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RealTimeMonitoringService:
    """Manages asyncio monitoring tasks for active campaigns.

    Each campaign gets an independent monitoring loop that collects metrics
    and checks alerts at a configurable interval.  Loop results are forwarded
    to the WebSocket broadcast queue for connected clients.
    """

    def __init__(
        self,
        metrics_collection_service: Any,
        alert_service: Any,
        broadcast_callback: Any | None = None,
    ) -> None:
        self._metrics_svc = metrics_collection_service
        self._alert_svc = alert_service
        self._broadcast = broadcast_callback  # called as await _broadcast(campaign_id, data)
        self._tasks: dict[str, asyncio.Task] = {}
        self._stats: dict[str, Any] = {
            "total_metrics_collected": 0,
            "alerts_triggered": 0,
            "start_time": time.monotonic(),
        }

    # ── Public API ─────────────────────────────────────────────────────────────

    async def start_monitoring(
        self,
        campaign_id: str,
        check_interval_seconds: int = 60,
        max_duration_minutes: int = 1440,
    ) -> asyncio.Task:
        """Start or replace the monitoring task for *campaign_id*."""
        if campaign_id in self._tasks and not self._tasks[campaign_id].done():
            logger.info("Replacing existing monitor for campaign %s", campaign_id)
            await self.stop_monitoring(campaign_id)

        task = asyncio.ensure_future(
            self._monitoring_loop(campaign_id, check_interval_seconds, max_duration_minutes)
        )
        self._tasks[campaign_id] = task
        logger.info("Started monitoring campaign %s (interval=%ds)", campaign_id, check_interval_seconds)
        return task

    async def stop_monitoring(self, campaign_id: str) -> None:
        """Cancel the monitoring task for *campaign_id*."""
        task = self._tasks.pop(campaign_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped monitoring campaign %s", campaign_id)

    async def get_monitoring_status(self, campaign_id: str) -> dict[str, Any]:
        task = self._tasks.get(campaign_id)
        return {
            "campaign_id": campaign_id,
            "is_monitoring": bool(task and not task.done()),
            "last_check": None,
            "next_check": None,
            "duration_remaining_minutes": None,
        }

    async def get_monitoring_stats(self) -> dict[str, Any]:
        active = sum(1 for t in self._tasks.values() if not t.done())
        uptime = time.monotonic() - self._stats["start_time"]
        return {
            "active_monitors": active,
            "total_metrics_collected": self._stats["total_metrics_collected"],
            "alerts_triggered": self._stats["alerts_triggered"],
            "uptime_seconds": round(uptime, 1),
        }

    async def broadcast_metrics_update(
        self, campaign_id: str, metrics: dict[str, Any]
    ) -> None:
        """Forward metrics to the registered broadcast callback (WebSocket manager)."""
        if self._broadcast:
            try:
                await self._broadcast(campaign_id, metrics)
            except Exception as exc:
                logger.warning("Broadcast failed for campaign %s: %s", campaign_id, exc)

    # ── Private ────────────────────────────────────────────────────────────────

    async def _monitoring_loop(
        self,
        campaign_id: str,
        check_interval: int,
        max_duration_minutes: int,
    ) -> None:
        deadline = time.monotonic() + max_duration_minutes * 60
        while time.monotonic() < deadline:
            try:
                metrics = await self._metrics_svc.collect_campaign_metrics(
                    campaign_id, force_refresh=True
                )
                self._stats["total_metrics_collected"] += 1
                await self.broadcast_metrics_update(campaign_id, metrics)

                alerts = await self._alert_svc.check_and_trigger_alerts(campaign_id)
                self._stats["alerts_triggered"] += len(alerts)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Monitoring loop error for campaign %s: %s", campaign_id, exc)

            try:
                await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                break

        logger.info("Monitoring loop finished for campaign %s", campaign_id)
