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

    # ── Mock API helpers ──────────────────────────────────────────

    async def find_by_mock_campaign_id(
        self, mock_campaign_id: str
    ) -> list[CampaignVariant]:
        """Find variants linked to a Mock API campaign ID."""
        return await self.find_all(
            filter={"mock_campaign_id": mock_campaign_id}, limit=10_000
        )

    async def update_mock_campaign_id(
        self, variant_id: str, mock_campaign_id: str
    ) -> Optional[CampaignVariant]:
        """Set mock_campaign_id after scheduling via Mock API."""
        return await self.update(
            variant_id,
            {"mock_campaign_id": mock_campaign_id},
        )

    async def get_variants_ready_for_execution(
        self, campaign_id: str
    ) -> list[CampaignVariant]:
        """Return SCHEDULED variants that have customer_ids assigned."""
        return await self.find_all(
            filter={
                "campaign_id": campaign_id,
                "status": VariantStatus.SCHEDULED.value,
                "customer_ids.0": {"$exists": True},
            },
            limit=10_000,
        )

    # ── Existing specialised queries ──────────────────────────────

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
            {"$set": {"status": new_status.value}},
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
