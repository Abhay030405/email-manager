"""Repository for campaign variant data access."""

import logging
from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.variant import CampaignVariant, VariantStatus

logger = logging.getLogger(__name__)


class VariantRepository(BaseRepository[CampaignVariant]):
    """Data access layer for the campaign_variants collection."""

    COLLECTION = "campaign_variants"
    ID_FIELD = "variant_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, CampaignVariant)

    # ── Specialised queries ───────────────────────────────────────

    async def find_by_campaign(
        self, campaign_id: str
    ) -> list[CampaignVariant]:
        """Find all variants for a campaign."""
        return await self.find_all(filter={"campaign_id": campaign_id}, limit=10_000)

    async def find_by_segment(self, segment_name: str) -> list[CampaignVariant]:
        """Find all variants targeting a specific segment."""
        return await self.find_all(
            filter={"segment_name": segment_name}, limit=10_000
        )

    async def update_status_bulk(
        self, variant_ids: list[str], new_status: VariantStatus
    ) -> int:
        """Update the status of multiple variants at once. Returns modified count."""
        if not variant_ids:
            return 0
        result = await self.collection.update_many(
            {"variant_id": {"$in": variant_ids}},
            {"$set": {"status": new_status.value, "updated_at": datetime.utcnow()}},
        )
        logger.info(
            "Bulk status update: %d variants -> %s", result.modified_count, new_status.value
        )
        return result.modified_count

    async def get_scheduled_variants(
        self, start: datetime, end: datetime
    ) -> list[CampaignVariant]:
        """Return variants scheduled to send within a datetime range."""
        return await self.find_all(
            filter={
                "status": VariantStatus.SCHEDULED.value,
                "send_time": {"$gte": start, "$lte": end},
            },
            limit=10_000,
        )
