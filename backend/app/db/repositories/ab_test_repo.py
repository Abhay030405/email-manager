"""Repository for ABTest documents."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.ab_test import ABTest


class ABTestRepository(BaseRepository[ABTest]):
    COLLECTION = "ab_tests"
    ID_FIELD = "test_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, ABTest)

    async def list_by_campaign(
        self,
        campaign_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ABTest]:
        cursor = (
            self.collection.find({"campaign_id": campaign_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [ABTest(**doc) async for doc in cursor]

    async def get_active_test(self, campaign_id: str) -> Optional[ABTest]:
        """Return the most recent test still within its test window."""
        now = datetime.utcnow()
        doc = await self.collection.find_one(
            {
                "campaign_id": campaign_id,
                "test_start_time": {"$lte": now},
                "test_end_time": {"$gte": now},
            },
            sort=[("created_at", -1)],
        )
        return ABTest(**doc) if doc else None

    async def update_results(self, test_id: str, results: dict[str, Any]) -> Optional[ABTest]:
        return await self.update(test_id, results)
