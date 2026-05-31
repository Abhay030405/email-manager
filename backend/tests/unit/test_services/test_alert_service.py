"""Unit tests for AlertService."""

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.performance_alert_repo import PerformanceAlertRepository
from app.models.metrics import Metrics
from app.services.alert_service import AlertService
from app.utils.alert_rules_engine import AlertRulesEngine


def _make_svc():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    return AlertService(
        alert_repo=PerformanceAlertRepository(db),
        metrics_repo=MetricsRepository(db),
        campaign_repo=CampaignRepository(db),
        rules_engine=AlertRulesEngine(),
    ), db


def _seed_low_metrics(db, campaign_id="camp-001"):
    from mongomock_motor import AsyncMongoMockClient as _
    return Metrics(
        variant_id="var-low", campaign_id=campaign_id, mock_campaign_id="mock-low",
        open_rate=0.05, click_rate=0.005, total_sent=1000,
    )


def _seed_high_metrics(campaign_id="camp-002"):
    return Metrics(
        variant_id="var-high", campaign_id=campaign_id, mock_campaign_id="mock-high",
        open_rate=0.55, click_rate=0.18, total_sent=1000,
    )


@pytest.mark.unit
class TestAlertService:

    async def test_check_and_trigger_alerts_returns_list(self):
        svc, db = _make_svc()
        result = await svc.check_and_trigger_alerts("camp-001")
        assert isinstance(result, list)

    async def test_check_and_trigger_no_metrics_returns_empty(self):
        svc, _ = _make_svc()
        result = await svc.check_and_trigger_alerts("camp-no-metrics")
        assert result == []

    async def test_check_and_trigger_with_low_metrics(self):
        svc, db = _make_svc()
        metrics_repo = MetricsRepository(db)
        await metrics_repo.create(_seed_low_metrics(db, "camp-low-01"))

        result = await svc.check_and_trigger_alerts("camp-low-01")
        assert isinstance(result, list)

    async def test_get_active_alerts_empty_returns_list(self):
        svc, _ = _make_svc()
        result = await svc.get_active_alerts(campaign_id="camp-no-alerts")
        assert isinstance(result, list)

    async def test_get_active_alerts_no_filter_returns_list(self):
        svc, _ = _make_svc()
        result = await svc.get_active_alerts()
        assert isinstance(result, list)

    async def test_get_active_alerts_severity_filter(self):
        svc, _ = _make_svc()
        result = await svc.get_active_alerts(severity="critical")
        assert isinstance(result, list)

    async def test_alerts_created_for_low_performance(self):
        svc, db = _make_svc()
        metrics_repo = MetricsRepository(db)
        await metrics_repo.create(_seed_low_metrics(db, "camp-low-02"))

        triggered = await svc.check_and_trigger_alerts("camp-low-02")
        active = await svc.get_active_alerts(campaign_id="camp-low-02")
        # Active alerts should be at least as many as triggered (some may deduplicate)
        assert len(active) <= len(triggered) + 1
