"""Repository for MetricAggregation documents."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.metric_aggregation import MetricAggregation


class MetricAggregationRepository(BaseRepository[MetricAggregation]):
    COLLECTION = "metric_aggregations"
    ID_FIELD = "aggregation_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, MetricAggregation)

    async def get_by_campaign(self, campaign_id: str) -> Optional[MetricAggregation]:
        doc = await self.collection.find_one(
            {"campaign_id": campaign_id, "aggregation_type": "campaign_total"},
            sort=[("last_updated", -1)],
        )
        return MetricAggregation(**doc) if doc else None

    async def get_by_segment(
        self, campaign_id: str, segment_name: str
    ) -> Optional[MetricAggregation]:
        doc = await self.collection.find_one(
            {
                "campaign_id": campaign_id,
                "aggregation_type": "segment",
                "aggregation_key": segment_name,
            },
            sort=[("last_updated", -1)],
        )
        return MetricAggregation(**doc) if doc else None

    async def get_by_variant(
        self, campaign_id: str, variant_id: str
    ) -> Optional[MetricAggregation]:
        doc = await self.collection.find_one(
            {
                "campaign_id": campaign_id,
                "aggregation_type": "variant",
                "aggregation_key": variant_id,
            },
            sort=[("last_updated", -1)],
        )
        return MetricAggregation(**doc) if doc else None

    async def list_by_period(
        self,
        aggregation_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list[MetricAggregation]:
        cursor = self.collection.find(
            {
                "aggregation_type": aggregation_type,
                "period_start": {"$gte": period_start},
                "period_end": {"$lte": period_end},
            }
        ).sort("period_start", 1)
        return [MetricAggregation(**doc) async for doc in cursor]

    async def upsert_for_campaign(
        self, campaign_id: str, aggregation_type: str, aggregation_key: str, data: dict
    ) -> MetricAggregation:
        """Upsert an aggregation record."""
        data["last_updated"] = datetime.utcnow()
        await self.collection.update_one(
            {
                "campaign_id": campaign_id,
                "aggregation_type": aggregation_type,
                "aggregation_key": aggregation_key,
            },
            {"$set": data, "$setOnInsert": {"aggregation_id": data.get("aggregation_id"), "created_at": datetime.utcnow()}},
            upsert=True,
        )
        doc = await self.collection.find_one(
            {"campaign_id": campaign_id, "aggregation_type": aggregation_type, "aggregation_key": aggregation_key}
        )
        return MetricAggregation(**doc)
