"""Repository for ExecutionLog documents."""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.execution_log import ExecutionLog, ExecutionLogStatus


class ExecutionLogRepository(BaseRepository[ExecutionLog]):
    COLLECTION = "execution_logs"
    ID_FIELD = "log_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, ExecutionLog)

    async def find_by_campaign(self, campaign_id: str) -> list[ExecutionLog]:
        """Return all logs for a campaign, newest first."""
        cursor = self.collection.find({"campaign_id": campaign_id}).sort("executed_at", -1)
        return [ExecutionLog(**doc) async for doc in cursor]

    async def find_by_variant(self, variant_id: str) -> list[ExecutionLog]:
        cursor = self.collection.find({"variant_id": variant_id}).sort("executed_at", -1)
        return [ExecutionLog(**doc) async for doc in cursor]

    async def find_failed(self, campaign_id: str) -> list[ExecutionLog]:
        """Return failed logs for a campaign (candidates for retry)."""
        cursor = self.collection.find(
            {"campaign_id": campaign_id, "status": ExecutionLogStatus.FAILED.value}
        ).sort("executed_at", -1)
        return [ExecutionLog(**doc) async for doc in cursor]

    async def count_by_status(self, campaign_id: str) -> dict[str, int]:
        """Return a status → count breakdown for a campaign."""
        pipeline: list[dict[str, Any]] = [
            {"$match": {"campaign_id": campaign_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        counts: dict[str, int] = {}
        async for doc in self.collection.aggregate(pipeline):
            counts[doc["_id"]] = doc["count"]
        return counts
