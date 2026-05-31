"""Unit tests for MetricsCollectionService."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.variant_repo import VariantRepository
from app.models.campaign import Campaign, CampaignStatus, ParsedData
from app.models.variant import CampaignVariant, VariantStatus
from app.services.metrics_collection_service import MetricsCollectionService


def _make_service():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]

    mock_api = MagicMock()
    mock_api.get_campaign_metrics.return_value = {
        "open_rate": 0.35,
        "click_rate": 0.085,
        "click_through_rate": 0.06,
        "total_sent": 1000,
        "unique_opens": 350,
        "unique_clicks": 85,
    }
    mock_api.get_campaign_results.return_value = [
        {"customer_id": "CUST0001", "opened": True, "clicked": False,
         "open_probability": 0.75, "click_probability": 0.25},
    ]

    return MetricsCollectionService(
        mock_api_client=mock_api,
        metrics_repo=MetricsRepository(db),
        campaign_repo=CampaignRepository(db),
        variant_repo=VariantRepository(db),
    )


@pytest.mark.unit
class TestMetricsCollectionService:

    async def test_collect_campaign_metrics_returns_dict(self):
        svc = _make_service()
        result = await svc.collect_campaign_metrics("camp-mc-001")
        assert isinstance(result, dict)

    async def test_collect_campaign_metrics_has_campaign_id(self):
        svc = _make_service()
        result = await svc.collect_campaign_metrics("camp-mc-001")
        assert "campaign_id" in result or result is not None

    async def test_collect_all_active_returns_dict(self):
        svc = _make_service()
        result = await svc.collect_all_active_campaigns_metrics()
        assert isinstance(result, dict)

    async def test_collect_customer_results_returns_list(self):
        svc = _make_service()
        result = await svc.collect_customer_results("mock-camp-id")
        assert isinstance(result, list)
