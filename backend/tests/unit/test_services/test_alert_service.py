"""Unit tests for AlertService."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.services.alert_service import AlertService
from app.models.metrics import Metrics


@pytest_asyncio.fixture
async def alert_service():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    service = AlertService(db=db)
    yield service
    client.close()


@pytest.mark.unit
class TestAlertService:

    @pytest.mark.asyncio
    async def test_check_for_alerts_low_performance(self, alert_service, sample_metrics_low_performer):
        alerts = await alert_service.check_for_alerts(
            sample_metrics_low_performer, campaign_id="camp-001"
        )
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_check_for_alerts_good_performance_no_critical_alerts(
        self, alert_service, sample_metrics_high_performer
    ):
        alerts = await alert_service.check_for_alerts(
            sample_metrics_high_performer, campaign_id="camp-001"
        )
        critical = [a for a in alerts if a.get("severity") == "critical"]
        assert len(critical) == 0

    @pytest.mark.asyncio
    async def test_list_active_alerts(self, alert_service):
        result = await alert_service.list_active_alerts(campaign_id="camp-001")
        assert isinstance(result, list)
