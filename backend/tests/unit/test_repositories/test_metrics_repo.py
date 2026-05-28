"""Unit tests for MetricsRepository."""

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.metrics_repo import MetricsRepository
from app.models.metrics import Metrics


@pytest_asyncio.fixture
async def metrics_repo():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    yield MetricsRepository(db)
    client.close()


def _make_metrics(metric_id: str = "met-001", **kw) -> Metrics:
    return Metrics(
        metric_id=metric_id,
        variant_id=kw.get("variant_id", "var-001"),
        campaign_id=kw.get("campaign_id", "camp-001"),
        mock_campaign_id=kw.get("mock_campaign_id", "mock-001"),
        open_rate=kw.get("open_rate", 0.35),
        click_rate=kw.get("click_rate", 0.085),
        click_through_rate=kw.get("click_through_rate", 0.06),
        total_sent=kw.get("total_sent", 1000),
        unique_opens=kw.get("unique_opens", 350),
        unique_clicks=kw.get("unique_clicks", 85),
    )


@pytest.mark.unit
class TestMetricsRepository:

    @pytest.mark.asyncio
    async def test_create_metrics(self, metrics_repo):
        m = _make_metrics("met-create-01")
        result = await metrics_repo.create(m)
        assert result.metric_id == "met-create-01"

    @pytest.mark.asyncio
    async def test_find_by_id(self, metrics_repo):
        m = _make_metrics("met-find-01")
        await metrics_repo.create(m)
        found = await metrics_repo.find_by_id("met-find-01")
        assert found is not None
        assert found.open_rate == 0.35

    @pytest.mark.asyncio
    async def test_find_by_campaign(self, metrics_repo):
        await metrics_repo.create(_make_metrics("met-camp-1", campaign_id="camp-abc"))
        await metrics_repo.create(_make_metrics("met-camp-2", campaign_id="camp-abc"))

        results = await metrics_repo.find_all(filter={"campaign_id": "camp-abc"})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_find_by_variant(self, metrics_repo):
        await metrics_repo.create(_make_metrics("met-var-1", variant_id="var-x"))
        results = await metrics_repo.find_all(filter={"variant_id": "var-x"})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_count(self, metrics_repo):
        for i in range(5):
            await metrics_repo.create(_make_metrics(f"met-count-{i}"))
        total = await metrics_repo.count()
        assert total >= 5

    @pytest.mark.asyncio
    async def test_delete_metrics(self, metrics_repo):
        m = _make_metrics("met-del-01")
        await metrics_repo.create(m)
        deleted = await metrics_repo.delete("met-del-01")
        assert deleted is True
        assert await metrics_repo.find_by_id("met-del-01") is None
