"""Repository for AnalyticsSnapshot documents."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.analytics_snapshot import AnalyticsSnapshot


class AnalyticsRepository(BaseRepository[AnalyticsSnapshot]):
    COLLECTION = "analytics_snapshots"
    ID_FIELD = "snapshot_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, AnalyticsSnapshot)

    async def create_snapshot(self, snapshot: AnalyticsSnapshot) -> AnalyticsSnapshot:
        return await self.create(snapshot)

    async def get_latest_snapshot(self, campaign_id: str) -> Optional[AnalyticsSnapshot]:
        doc = await self.collection.find_one(
            {"campaign_id": campaign_id},
            sort=[("snapshot_timestamp", -1)],
        )
        return AnalyticsSnapshot(**doc) if doc else None

    async def list_snapshots(
        self,
        campaign_id: str,
        days: int = 7,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AnalyticsSnapshot]:
        since = datetime.utcnow() - timedelta(days=days)
        cursor = (
            self.collection.find(
                {"campaign_id": campaign_id, "snapshot_timestamp": {"$gte": since}}
            )
            .sort("snapshot_timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        return [AnalyticsSnapshot(**doc) async for doc in cursor]
