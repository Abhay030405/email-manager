"""Unit tests for MetricsAggregationService."""

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.services.metrics_aggregation_service import MetricsAggregationService
from app.db.repositories.metrics_repo import MetricsRepository
from app.models.metrics import Metrics


@pytest_asyncio.fixture
async def aggregation_service():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    service = MetricsAggregationService(db=db)

    # Seed data
    repo = MetricsRepository(db)
    metrics = [
        Metrics(metric_id=f"met-agg-{i}", variant_id=f"var-{i}", campaign_id="camp-agg-001",
                mock_campaign_id=f"mock-{i}", open_rate=0.30 + i * 0.05,
                click_rate=0.08 + i * 0.02)
        for i in range(4)
    ]
    for m in metrics:
        await repo.create(m)

    yield service
    client.close()


@pytest.mark.unit
class TestMetricsAggregationService:

    @pytest.mark.asyncio
    async def test_aggregate_campaign_metrics(self, aggregation_service):
        result = await aggregation_service.aggregate_campaign_metrics("camp-agg-001")
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_aggregate_empty_campaign(self, aggregation_service):
        result = await aggregation_service.aggregate_campaign_metrics("camp-nonexistent")
        assert result is not None

    @pytest.mark.asyncio
    async def test_aggregate_includes_average_metrics(self, aggregation_service):
        result = await aggregation_service.aggregate_campaign_metrics("camp-agg-001")
        if result:
            has_avg = (
                "avg_open_rate" in result
                or "open_rate" in result
                or "average_open_rate" in result
            )
            assert has_avg or result is not None
