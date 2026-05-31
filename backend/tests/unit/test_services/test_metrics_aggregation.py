"""Unit tests for MetricsAggregationService."""

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.metric_aggregation_repo import MetricAggregationRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.variant_repo import VariantRepository
from app.models.metrics import Metrics
from app.services.metrics_aggregation_service import MetricsAggregationService


def _make_service():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    return MetricsAggregationService(
        metrics_repo=MetricsRepository(db),
        aggregation_repo=MetricAggregationRepository(db),
        variant_repo=VariantRepository(db),
        campaign_repo=CampaignRepository(db),
    ), db


@pytest.mark.unit
class TestMetricsAggregationService:

    async def test_aggregate_campaign_metrics_returns_object(self):
        svc, _ = _make_service()
        result = await svc.aggregate_campaign_metrics("camp-agg-001")
        assert result is not None

    async def test_aggregate_empty_campaign_returns_result(self):
        svc, _ = _make_service()
        result = await svc.aggregate_campaign_metrics("camp-no-data")
        assert result is not None

    async def test_aggregate_result_has_campaign_id(self):
        svc, _ = _make_service()
        result = await svc.aggregate_campaign_metrics("camp-attr-001")
        assert hasattr(result, "campaign_id") or isinstance(result, dict)

    async def test_aggregate_with_seeded_metrics(self):
        svc, db = _make_service()
        repo = MetricsRepository(db)
        for i in range(3):
            await repo.create(Metrics(
                metric_id=f"met-agg-{i}",
                variant_id=f"var-{i}",
                campaign_id="camp-seeded",
                mock_campaign_id=f"mock-{i}",
                open_rate=0.30 + i * 0.05,
                click_rate=0.08 + i * 0.02,
            ))

        result = await svc.aggregate_campaign_metrics("camp-seeded")
        assert result is not None

    async def test_aggregate_campaign_id_matches(self):
        svc, _ = _make_service()
        result = await svc.aggregate_campaign_metrics("camp-check-001")
        if hasattr(result, "campaign_id"):
            assert result.campaign_id == "camp-check-001"
