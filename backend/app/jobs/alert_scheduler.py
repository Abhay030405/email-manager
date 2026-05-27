"""Periodic alert check scheduler — evaluates rules against active campaigns."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AlertScheduler:
    """Schedules periodic alert checks using asyncio (no external library)."""

    def __init__(
        self,
        alert_service: Any,
        campaign_repo: Any,
        interval_seconds: int = 300,
    ) -> None:
        self._alert_svc = alert_service
        self._campaign_repo = campaign_repo
        self._interval = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self) -> None:
        if self._task and not self._task.done():
            logger.warning("AlertScheduler already running")
            return
        self._running = True
        self._task = asyncio.ensure_future(self._loop())
        logger.info("AlertScheduler started (interval=%ds)", self._interval)

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("AlertScheduler stopped")

    async def run_once(self) -> dict:
        return await self.job_check_active_campaigns_alerts()

    async def job_check_active_campaigns_alerts(self) -> dict:
        """Check all active campaigns for alert rule violations."""
        from app.models.campaign import CampaignStatus

        logger.info("AlertScheduler: checking active campaigns for alerts")
        try:
            campaigns = await self._campaign_repo.find_all(
                filter={"status": {"$in": [
                    CampaignStatus.EXECUTING.value,
                    CampaignStatus.COMPLETED.value,
                ]}}
            )
            total_alerts = 0
            errors: list[str] = []
            for campaign in campaigns:
                try:
                    alerts = await self._alert_svc.check_and_trigger_alerts(campaign.campaign_id)
                    total_alerts += len(alerts)
                except Exception as exc:
                    errors.append(f"{campaign.campaign_id}: {exc}")

            logger.info("AlertScheduler: %d alerts triggered across %d campaigns", total_alerts, len(campaigns))
            return {"campaigns_checked": len(campaigns), "alerts_triggered": total_alerts, "errors": errors}
        except Exception as exc:
            logger.error("AlertScheduler: job failed: %s", exc)
            return {"error": str(exc)}

    async def _loop(self) -> None:
        while self._running:
            await self.job_check_active_campaigns_alerts()
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
