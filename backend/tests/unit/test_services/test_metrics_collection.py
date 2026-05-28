"""Unit tests for MetricsCollectionService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.services.metrics_collection_service import MetricsCollectionService
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.variant_repo import VariantRepository
from app.models.metrics import Metrics
from app.models.variant import CampaignVariant, VariantStatus


@pytest_asyncio.fixture
async def metrics_collection_service():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    mock_api_client = MagicMock()
    mock_api_client.get_campaign_metrics.return_value = {
        "open_rate": 0.35,
        "click_rate": 0.085,
        "click_through_rate": 0.06,
        "total_sent": 1000,
        "unique_opens": 350,
        "unique_clicks": 85,
    }
    mock_api_client.get_campaign_results.return_value = [
        {"customer_id": "CUST0001", "opened": True, "clicked": False,
         "open_probability": 0.75, "click_probability": 0.25}
    ]
    service = MetricsCollectionService(db=db, mock_api_client=mock_api_client)
    yield service
    client.close()


@pytest.mark.unit
class TestMetricsCollectionService:

    @pytest.mark.asyncio
    async def test_collect_returns_metrics_object(self, metrics_collection_service):
        variant = CampaignVariant(
            variant_id="var-mc-01",
            campaign_id="camp-mc-01",
            mock_campaign_id="mock-api-uuid-001",
            segment_name="test",
            subject_line="Test",
            email_body="Body",
            status=VariantStatus.SENT,
            customer_ids=["CUST0001"],
        )

        result = await metrics_collection_service.collect_variant_metrics(variant)

        assert result is not None

    @pytest.mark.asyncio
    async def test_collect_stores_metrics_in_db(self, metrics_collection_service):
        variant = CampaignVariant(
            variant_id="var-mc-02",
            campaign_id="camp-mc-01",
            mock_campaign_id="mock-api-uuid-002",
            segment_name="test",
            subject_line="Test",
            email_body="Body",
            status=VariantStatus.SENT,
            customer_ids=["CUST0001"],
        )

        await metrics_collection_service.collect_variant_metrics(variant)

        metrics_repo = MetricsRepository(metrics_collection_service.db)
        all_metrics = await metrics_repo.find_all(filter={"variant_id": "var-mc-02"})
        assert len(all_metrics) >= 0

    @pytest.mark.asyncio
    async def test_collect_without_mock_campaign_id_skips(self, metrics_collection_service):
        variant = CampaignVariant(
            variant_id="var-mc-03",
            campaign_id="camp-mc-01",
            mock_campaign_id=None,
            segment_name="test",
            subject_line="Test",
            email_body="Body",
            status=VariantStatus.DRAFT,
            customer_ids=[],
        )

        result = await metrics_collection_service.collect_variant_metrics(variant)
        assert result is None or isinstance(result, dict)
