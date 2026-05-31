"""Unit tests for OptimizationRepository."""

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.optimization_repo import OptimizationRepository
from app.models.optimization import OptimizationResult


@pytest_asyncio.fixture
async def optimization_repo():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    yield OptimizationRepository(db)
    client.close()


@pytest.mark.unit
class TestOptimizationRepository:

    async def test_create_optimization(self, optimization_repo):
        opt = OptimizationResult(
            campaign_id="camp-opt-001",
            poor_performer_variants=["var-002"],
            regenerated_variants=[{"variant_id": "var-new-001"}],
            improvement_percentage=12.5,
        )
        result = await optimization_repo.create(opt)
        assert result is not None
        assert result.campaign_id == "camp-opt-001"

    async def test_find_by_id(self, optimization_repo):
        opt = OptimizationResult(
            campaign_id="camp-opt-002",
            iteration_number=1,
        )
        created = await optimization_repo.create(opt)
        found = await optimization_repo.find_by_id(created.result_id)
        assert found is not None
        assert found.result_id == created.result_id

    async def test_find_by_id_nonexistent(self, optimization_repo):
        result = await optimization_repo.find_by_id("nonexistent-id-xyz")
        assert result is None

    async def test_list_by_campaign(self, optimization_repo):
        for i in range(3):
            await optimization_repo.create(
                OptimizationResult(campaign_id="camp-list-001", iteration_number=i + 1)
            )

        results = await optimization_repo.list_by_campaign("camp-list-001")
        assert len(results) >= 3
        assert all(r.campaign_id == "camp-list-001" for r in results)

    async def test_list_by_campaign_empty(self, optimization_repo):
        results = await optimization_repo.list_by_campaign("camp-no-results")
        assert results == []

    async def test_get_latest_iteration(self, optimization_repo):
        await optimization_repo.create(OptimizationResult(campaign_id="camp-latest", iteration_number=1))
        await optimization_repo.create(OptimizationResult(campaign_id="camp-latest", iteration_number=2))
        await optimization_repo.create(OptimizationResult(campaign_id="camp-latest", iteration_number=3))

        latest = await optimization_repo.get_latest_iteration("camp-latest")
        assert latest is not None
        assert latest.iteration_number == 3

    async def test_get_latest_iteration_no_records(self, optimization_repo):
        result = await optimization_repo.get_latest_iteration("camp-no-records")
        assert result is None

    async def test_count_iterations(self, optimization_repo):
        for _ in range(4):
            await optimization_repo.create(OptimizationResult(campaign_id="camp-count-001"))

        count = await optimization_repo.count_iterations("camp-count-001")
        assert count >= 4

    async def test_update_optimization(self, optimization_repo):
        opt = OptimizationResult(campaign_id="camp-update-001", status="pending")
        created = await optimization_repo.create(opt)

        updated = await optimization_repo.update(
            created.result_id,
            {"status": "completed", "convergence_achieved": True}
        )
        assert updated is not None
        assert updated.status == "completed"
        assert updated.convergence_achieved is True
