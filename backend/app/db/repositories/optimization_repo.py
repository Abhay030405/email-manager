"""Repository for OptimizationResult documents."""

from __future__ import annotations

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.optimization import OptimizationResult


class OptimizationRepository(BaseRepository[OptimizationResult]):
    COLLECTION = "optimization_results"
    ID_FIELD = "result_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, OptimizationResult)

    async def list_by_campaign(
        self,
        campaign_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[OptimizationResult]:
        cursor = (
            self.collection.find({"campaign_id": campaign_id})
            .sort("iteration_number", -1)
            .skip(skip)
            .limit(limit)
        )
        return [OptimizationResult(**doc) async for doc in cursor]

    async def get_latest_iteration(self, campaign_id: str) -> Optional[OptimizationResult]:
        doc = await self.collection.find_one(
            {"campaign_id": campaign_id},
            sort=[("iteration_number", -1)],
        )
        return OptimizationResult(**doc) if doc else None

    async def get_iteration(
        self, campaign_id: str, iteration_number: int
    ) -> Optional[OptimizationResult]:
        doc = await self.collection.find_one(
            {"campaign_id": campaign_id, "iteration_number": iteration_number}
        )
        return OptimizationResult(**doc) if doc else None

    async def count_iterations(self, campaign_id: str) -> int:
        return await self.collection.count_documents({"campaign_id": campaign_id})
