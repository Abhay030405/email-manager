"""Unit tests for OptimizationRepository."""

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.optimization_repo import OptimizationRepository
from app.models.optimization import Optimization


@pytest_asyncio.fixture
async def optimization_repo():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    yield OptimizationRepository(db)
    client.close()


@pytest.mark.unit
class TestOptimizationRepository:

    @pytest.mark.asyncio
    async def test_create_optimization(self, optimization_repo):
        opt = Optimization(
            campaign_id="camp-opt-001",
            poor_performers=["var-002"],
            new_variants=["var-new-001"],
            improvement_percentage=12.5,
        )
        result = await optimization_repo.create(opt)
        assert result.campaign_id == "camp-opt-001"

    @pytest.mark.asyncio
    async def test_find_by_campaign(self, optimization_repo):
        opt1 = Optimization(campaign_id="camp-opt-find", iteration=1)
        opt2 = Optimization(campaign_id="camp-opt-find", iteration=2)
        await optimization_repo.create(opt1)
        await optimization_repo.create(opt2)

        results = await optimization_repo.find_all(filter={"campaign_id": "camp-opt-find"})
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_count_by_campaign(self, optimization_repo):
        for i in range(3):
            await optimization_repo.create(Optimization(campaign_id="camp-count-opt", iteration=i))

        total = await optimization_repo.count(filter={"campaign_id": "camp-count-opt"})
        assert total == 3
