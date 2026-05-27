"""Alert service — creates, manages, and acknowledges performance alerts."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.performance_alert_repo import PerformanceAlertRepository
from app.models.performance_alert import PerformanceAlert
from app.utils.alert_rules_engine import AlertRulesEngine

logger = logging.getLogger(__name__)


class AlertService:
    """Creates and manages performance alerts for campaign metrics."""

    def __init__(
        self,
        alert_repo: PerformanceAlertRepository,
        metrics_repo: MetricsRepository,
        campaign_repo: CampaignRepository,
        rules_engine: AlertRulesEngine,
    ) -> None:
        self.alert_repo = alert_repo
        self.metrics_repo = metrics_repo
        self.campaign_repo = campaign_repo
        self.rules_engine = rules_engine

    async def check_and_trigger_alerts(
        self, campaign_id: str
    ) -> list[PerformanceAlert]:
        """Evaluate current metrics against all rules and create new alerts."""
        metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
        if not metrics_list:
            return []

        trend = await self.metrics_repo.calculate_trend(campaign_id, "open_rate")
        created: list[PerformanceAlert] = []

        for metrics in metrics_list:
            violations = self.rules_engine.evaluate_rules(metrics, trend=trend)
            for v in violations:
                alert = await self.trigger_alert(
                    campaign_id=campaign_id,
                    alert_type=v["alert_type"],
                    severity=v["severity"],
                    threshold=v["threshold"],
                    actual_value=v["actual_value"],
                    variant_id=metrics.variant_id,
                    message=v["message"],
                    recommendation=v["recommendation"],
                )
                if alert:
                    created.append(alert)

        return created

    async def trigger_alert(
        self,
        campaign_id: str,
        alert_type: str,
        severity: str,
        threshold: float,
        actual_value: float,
        variant_id: Optional[str] = None,
        message: str = "",
        recommendation: str = "",
    ) -> Optional[PerformanceAlert]:
        """Create a new alert only if one doesn't already exist within the dedup window."""
        exists = await self.alert_repo.alert_exists(
            campaign_id, alert_type, variant_id=variant_id, within_minutes=60
        )
        if exists:
            logger.debug("Alert %s already exists for campaign %s — skipping", alert_type, campaign_id)
            return None

        alert = PerformanceAlert(
            campaign_id=campaign_id,
            variant_id=variant_id,
            alert_type=alert_type,
            severity=severity,
            threshold=threshold,
            actual_value=actual_value,
            triggered_at=datetime.utcnow(),
            message=message or f"{alert_type} alert for campaign {campaign_id}",
            recommendation=recommendation or self.rules_engine.get_recommendation(alert_type),
        )
        await self.alert_repo.create(alert)
        await self.notify_about_alert(alert)
        logger.info("Alert triggered: %s / %s for campaign %s", severity, alert_type, campaign_id)
        return alert

    async def acknowledge_alert(
        self,
        alert_id: str,
        user: str,
        notes: Optional[str] = None,
    ) -> Optional[PerformanceAlert]:
        """Mark alert as acknowledged."""
        alert = await self.alert_repo.acknowledge_alert(alert_id, user)
        if alert and notes:
            await self.alert_repo.update(alert_id, {"metadata": {"acknowledgement_notes": notes}})
        return alert

    async def get_active_alerts(
        self,
        campaign_id: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> list[PerformanceAlert]:
        """Return unacknowledged alerts, optionally filtered."""
        alerts = await self.alert_repo.list_active_alerts(campaign_id=campaign_id)
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    async def notify_about_alert(
        self,
        alert: PerformanceAlert,
        notification_channels: list[str] | None = None,
    ) -> None:
        """Log the alert. Future: email / Slack / webhook integration."""
        level = logging.CRITICAL if alert.severity == "critical" else logging.WARNING
        logger.log(
            level,
            "[ALERT] %s | campaign=%s variant=%s | actual=%.4f threshold=%.4f | %s",
            alert.alert_type,
            alert.campaign_id,
            alert.variant_id,
            alert.actual_value,
            alert.threshold,
            alert.recommendation,
        )
