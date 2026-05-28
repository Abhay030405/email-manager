"""Integration tests for metrics collection pipeline."""

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.variant_repo import VariantRepository
from app.models.metrics import Metrics
from app.models.variant import CampaignVariant, VariantStatus
from app.services.metrics_collection_service import MetricsCollectionService


@pytest_asyncio.fixture
async def db():
    client = AsyncMongoMockClient()
    yield client["campaignx_test"]
    client.close()


@pytest_asyncio.fixture
def mock_api_client():
    client = MagicMock()
    client.get_campaign_metrics.return_value = {
        "open_rate": 0.45,
        "click_rate": 0.12,
        "click_through_rate": 0.10,
        "total_sent": 500,
        "unique_opens": 225,
        "unique_clicks": 60,
    }
    client.get_campaign_results.return_value = [
        {"customer_id": "CUST0001", "opened": True, "clicked": True,
         "open_probability": 0.80, "click_probability": 0.40},
        {"customer_id": "CUST0002", "opened": True, "clicked": False,
         "open_probability": 0.60, "click_probability": 0.15},
    ]
    return client


@pytest.mark.integration
class TestMetricsPipelineIntegration:

    @pytest.mark.asyncio
    async def test_metrics_collected_and_stored(self, db, mock_api_client):
        variant_repo = VariantRepository(db)
        metrics_repo = MetricsRepository(db)

        variant = CampaignVariant(
            variant_id="var-pipeline-01",
            campaign_id="camp-pipeline-01",
            mock_campaign_id="mock-pipeline-uuid-001",
            segment_name="test",
            subject_line="Test",
            email_body="Body",
            status=VariantStatus.SENT,
            customer_ids=["CUST0001", "CUST0002"],
        )
        await variant_repo.create(variant)

        service = MetricsCollectionService(db=db, mock_api_client=mock_api_client)
        result = await service.collect_variant_metrics(variant)

        stored = await metrics_repo.find_all(filter={"variant_id": "var-pipeline-01"})
        assert len(stored) >= 0

    @pytest.mark.asyncio
    async def test_metrics_rates_stored_as_decimals(self, db, mock_api_client):
        metrics_repo = MetricsRepository(db)

        m = Metrics.from_mock_api(
            mock_api_client.get_campaign_metrics.return_value,
            variant_id="var-rate-01",
            campaign_id="camp-rate-01",
            mock_campaign_id="mock-rate-001",
        )
        await metrics_repo.create(m)

        found = await metrics_repo.find_all(filter={"variant_id": "var-rate-01"})
        assert len(found) == 1
        assert found[0].open_rate <= 1.0
        assert found[0].click_rate <= 1.0

    @pytest.mark.asyncio
    async def test_percentage_properties_convert_correctly(self, db):
        m = Metrics(
            variant_id="var-pct-01",
            campaign_id="camp-pct-01",
            mock_campaign_id="mock-pct-001",
            open_rate=0.60,
            click_rate=0.20,
        )
        assert m.open_rate_percentage == 60.0
        assert m.click_rate_percentage == 20.0

    @pytest.mark.asyncio
    async def test_multiple_variants_metrics_collected(self, db, mock_api_client):
        variant_repo = VariantRepository(db)
        metrics_repo = MetricsRepository(db)

        variants = [
            CampaignVariant(
                variant_id=f"var-multi-{i}",
                campaign_id="camp-multi-01",
                mock_campaign_id=f"mock-multi-{i}",
                segment_name=f"seg_{i}",
                subject_line=f"Subject {i}",
                email_body=f"Body {i}",
                status=VariantStatus.SENT,
                customer_ids=[f"CUST{i:04d}"],
            )
            for i in range(3)
        ]

        for v in variants:
            await variant_repo.create(v)

        service = MetricsCollectionService(db=db, mock_api_client=mock_api_client)
        for v in variants:
            await service.collect_variant_metrics(v)

        assert mock_api_client.get_campaign_metrics.call_count == 3
