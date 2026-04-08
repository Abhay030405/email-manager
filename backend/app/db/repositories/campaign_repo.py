"""Repository for campaign data access."""

from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.campaign import Campaign, CampaignStatus


class CampaignRepository(BaseRepository[Campaign]):
    """Data access layer for the campaigns collection."""

    COLLECTION = "campaigns"
    ID_FIELD = "campaign_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, Campaign)

    # ── Specialised queries ───────────────────────────────────────

    async def find_by_status(self, status: str) -> list[Campaign]:
        """Find campaigns by status."""
        return await self.find_all(filter={"status": status})

    async def update_status(
        self, campaign_id: str, new_status: CampaignStatus
    ) -> Optional[Campaign]:
        """Update only the status of a campaign."""
        update_data: dict[str, Any] = {
            "status": new_status.value,
            "updated_at": datetime.utcnow(),
        }
        if new_status == CampaignStatus.APPROVED:
            update_data["approved_at"] = datetime.utcnow()
        return await self.update(campaign_id, update_data)

    async def find_pending_approval(self) -> list[Campaign]:
        """Return campaigns waiting for approval."""
        return await self.find_all(
            filter={"status": CampaignStatus.PENDING_APPROVAL.value}
        )

    async def find_active_campaigns(self) -> list[Campaign]:
        """Return campaigns that are currently executing or optimizing."""
        return await self.find_all(
            filter={
                "status": {
                    "$in": [
                        CampaignStatus.EXECUTING.value,
                        CampaignStatus.OPTIMIZING.value,
                    ]
                }
            }
        )

    async def get_campaign_with_variants(
        self, campaign_id: str
    ) -> Optional[dict[str, Any]]:
        """Aggregate a campaign with its variants joined from campaign_variants."""
        pipeline = [
            {"$match": {"campaign_id": campaign_id}},
            {
                "$lookup": {
                    "from": "campaign_variants",
                    "localField": "campaign_id",
                    "foreignField": "campaign_id",
                    "as": "variants",
                }
            },
        ]
        cursor = self.collection.aggregate(pipeline)
        results = [doc async for doc in cursor]
        return results[0] if results else None

    async def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> list[Campaign]:
        """List campaigns with pagination, newest first."""
        cursor = (
            self.collection.find()
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [Campaign(**doc) async for doc in cursor]
        return await self.collection.count_documents(filter_query or {})
