"""Repository for segment data access."""

from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.segment import Segment


class SegmentRepository(BaseRepository[Segment]):
    """Data access layer for the segments collection."""

    COLLECTION = "segments"
    ID_FIELD = "segment_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, Segment)

    async def find_by_campaign(
        self, campaign_id: str, skip: int = 0, limit: int = 100
    ) -> list[Segment]:
        """Return all segments for a given campaign."""
        return await self.find_all(
            filter={"campaign_id": campaign_id}, skip=skip, limit=limit
        )

    async def find_by_name(
        self, campaign_id: str, segment_name: str
    ) -> Optional[Segment]:
        """Find a segment by name within a campaign."""
        doc = await self.collection.find_one(
            {"campaign_id": campaign_id, "segment_name": segment_name}
        )
        return Segment(**doc) if doc else None

    async def update_customer_ids(
        self, segment_id: str, customer_ids: list[str]
    ) -> Optional[Segment]:
        """Replace the customer list (and recalculate size) for a segment."""
        return await self.update(
            segment_id, {"customer_ids": customer_ids, "size": len(customer_ids)}
        )

    async def add_customers(
        self, segment_id: str, new_customer_ids: list[str]
    ) -> Optional[Segment]:
        """Append new customer IDs, deduplicating via $addToSet."""
        await self.collection.update_one(
            {"segment_id": segment_id},
            {"$addToSet": {"customer_ids": {"$each": new_customer_ids}}},
        )
        doc = await self.collection.find_one({"segment_id": segment_id})
        if doc is None:
            return None
        # Sync size field
        await self.collection.update_one(
            {"segment_id": segment_id},
            {"$set": {"size": len(doc.get("customer_ids", []))}},
        )
        doc = await self.collection.find_one({"segment_id": segment_id})
        return Segment(**doc) if doc else None

    async def get_segment_sizes(
        self, campaign_id: str
    ) -> list[dict[str, Any]]:
        """Return segment_id, segment_name, size for all campaign segments."""
        pipeline = [
            {"$match": {"campaign_id": campaign_id}},
            {
                "$project": {
                    "_id": 0,
                    "segment_id": 1,
                    "segment_name": 1,
                    "size": 1,
                }
            },
            {"$sort": {"size": -1}},
        ]
        cursor = self.collection.aggregate(pipeline)
        return [doc async for doc in cursor]

    async def delete_by_campaign(self, campaign_id: str) -> int:
        """Delete all segments for a campaign. Returns deleted count."""
        result = await self.collection.delete_many({"campaign_id": campaign_id})
        return result.deleted_count
