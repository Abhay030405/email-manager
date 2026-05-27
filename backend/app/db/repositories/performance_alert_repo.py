"""Repository for PerformanceAlert documents."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.performance_alert import PerformanceAlert


class PerformanceAlertRepository(BaseRepository[PerformanceAlert]):
    COLLECTION = "performance_alerts"
    ID_FIELD = "alert_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, PerformanceAlert)

    async def list_active_alerts(
        self,
        campaign_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PerformanceAlert]:
        """Return unacknowledged alerts, optionally filtered by campaign."""
        filt: dict[str, Any] = {"acknowledged": False}
        if campaign_id:
            filt["campaign_id"] = campaign_id
        cursor = self.collection.find(filt).sort("triggered_at", -1).skip(skip).limit(limit)
        return [PerformanceAlert(**doc) async for doc in cursor]

    async def list_by_campaign(
        self,
        campaign_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PerformanceAlert]:
        cursor = (
            self.collection.find({"campaign_id": campaign_id})
            .sort("triggered_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [PerformanceAlert(**doc) async for doc in cursor]

    async def acknowledge_alert(self, alert_id: str, user: str) -> Optional[PerformanceAlert]:
        """Mark alert as acknowledged."""
        return await self.update(
            alert_id,
            {
                "acknowledged": True,
                "acknowledged_by": user,
                "acknowledged_at": datetime.utcnow(),
            },
        )

    async def get_critical_alerts(self) -> list[PerformanceAlert]:
        cursor = (
            self.collection.find({"severity": "critical", "acknowledged": False})
            .sort("triggered_at", -1)
        )
        return [PerformanceAlert(**doc) async for doc in cursor]

    async def alert_exists(
        self,
        campaign_id: str,
        alert_type: str,
        variant_id: Optional[str] = None,
        within_minutes: int = 60,
    ) -> bool:
        """Return True if a matching unacknowledged alert already exists within the window."""
        since = datetime.utcnow() - timedelta(minutes=within_minutes)
        filt: dict[str, Any] = {
            "campaign_id": campaign_id,
            "alert_type": alert_type,
            "acknowledged": False,
            "triggered_at": {"$gte": since},
        }
        if variant_id:
            filt["variant_id"] = variant_id
        doc = await self.collection.find_one(filt)
        return doc is not None

    async def cleanup_old_alerts(self, days: int = 30) -> int:
        """Delete acknowledged alerts older than *days* days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.collection.delete_many(
            {"acknowledged": True, "triggered_at": {"$lt": cutoff}}
        )
        return result.deleted_count
