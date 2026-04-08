"""Repository for metrics data access."""

import logging
from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.metrics import Metrics

logger = logging.getLogger(__name__)


class MetricsRepository(BaseRepository[Metrics]):
    """Data access layer for the metrics collection."""

    COLLECTION = "metrics"
    ID_FIELD = "metric_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, Metrics)

    # ── Specialised queries ───────────────────────────────────────

    async def find_by_variant(self, variant_id: str) -> Optional[Metrics]:
        """Find the most recent metrics for a specific variant."""
        doc = await self.collection.find_one(
            {"variant_id": variant_id}, sort=[("timestamp", -1)]
        )
        return Metrics(**doc) if doc else None

    async def find_by_campaign(self, campaign_id: str) -> list[Metrics]:
        """Find all metrics for a campaign."""
        return await self.find_all(filter={"campaign_id": campaign_id}, limit=10_000)

    async def get_top_performers(
        self, limit: int = 5, min_score: float = 0.0
    ) -> list[Metrics]:
        """Get top-performing variants ordered by performance_score desc."""
        cursor = (
            self.collection.find({"performance_score": {"$gte": min_score}})
            .sort("performance_score", -1)
            .limit(limit)
        )
        return [Metrics(**doc) async for doc in cursor]

    async def get_bottom_performers(
        self, limit: int = 5, max_score: float = 100.0
    ) -> list[Metrics]:
        """Get lowest-performing variants ordered by performance_score asc."""
        cursor = (
            self.collection.find({"performance_score": {"$lte": max_score}})
            .sort("performance_score", 1)
            .limit(limit)
        )
        return [Metrics(**doc) async for doc in cursor]

    async def calculate_campaign_aggregates(
        self, campaign_id: str
    ) -> dict[str, Any]:
        """
        Aggregate average metrics for a campaign.

        Returns dict with keys: avg_open_rate, avg_click_rate,
        avg_performance_score, total_sent, total_opened, total_clicked.
        """
        pipeline = [
            {"$match": {"campaign_id": campaign_id}},
            {
                "$group": {
                    "_id": "$campaign_id",
                    "avg_open_rate": {"$avg": "$open_rate"},
                    "avg_click_rate": {"$avg": "$click_rate"},
                    "avg_performance_score": {"$avg": "$performance_score"},
                    "total_sent": {"$sum": "$emails_sent"},
                    "total_opened": {"$sum": "$emails_opened"},
                    "total_clicked": {"$sum": "$emails_clicked"},
                }
            },
        ]
        cursor = self.collection.aggregate(pipeline)
        results = [doc async for doc in cursor]
        if not results:
            return {
                "avg_open_rate": 0.0,
                "avg_click_rate": 0.0,
                "avg_performance_score": 0.0,
                "total_sent": 0,
                "total_opened": 0,
                "total_clicked": 0,
            }
        agg = results[0]
        agg.pop("_id", None)
        return agg

    async def get_metrics_time_series(
        self,
        campaign_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Metrics]:
        """Return metrics for a campaign within a time window, chronologically."""
        cursor = (
            self.collection.find(
                {
                    "campaign_id": campaign_id,
                    "timestamp": {"$gte": start_date, "$lte": end_date},
                }
            )
            .sort("timestamp", 1)
        )
        return [Metrics(**doc) async for doc in cursor]
