"""Repository for metrics data access — Mock Campaign API-aligned."""

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

    # ── Mock API helpers ──────────────────────────────────────────

    async def create_from_mock_api(self, metrics: Metrics) -> Metrics:
        """Insert metrics created via Metrics.from_mock_api()."""
        return await self.create(metrics)

    async def upsert(self, metrics: Metrics) -> Metrics:
        """Upsert metrics by variant_id — update if exists, insert otherwise."""
        doc = metrics.model_dump()
        await self.collection.update_one(
            {"variant_id": metrics.variant_id},
            {"$set": doc},
            upsert=True,
        )
        return metrics

    async def update_from_mock_api(
        self, mock_campaign_id: str, data: dict[str, Any]
    ) -> Optional[Metrics]:
        """Update existing metrics row by mock_campaign_id with new API data."""
        doc = await self.collection.find_one({"mock_campaign_id": mock_campaign_id})
        if doc is None:
            return None
        update_fields = {
            "open_rate": float(data.get("open_rate", 0)),
            "click_rate": float(data.get("click_rate", 0)),
            "click_through_rate": float(data.get("click_through_rate", 0)),
            "total_sent": int(data.get("total_sent", 0)),
            "unique_opens": int(data.get("unique_opens", 0)),
            "unique_clicks": int(data.get("unique_clicks", 0)),
            "collected_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
        }
        return await self.update(doc["metric_id"], update_fields)

    async def get_latest_by_mock_campaign_id(
        self, mock_campaign_id: str
    ) -> Optional[Metrics]:
        """Return the most recent metrics for a Mock API campaign."""
        doc = await self.collection.find_one(
            {"mock_campaign_id": mock_campaign_id},
            sort=[("calculated_at", -1)],
        )
        return Metrics(**doc) if doc else None

    # ── Existing queries (updated field names) ────────────────────

    async def find_by_variant(self, variant_id: str) -> Optional[Metrics]:
        """Find the most recent metrics for a specific variant."""
        doc = await self.collection.find_one(
            {"variant_id": variant_id}, sort=[("calculated_at", -1)]
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
        self, limit: int = 5, max_score: float = 1.0
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
        """Aggregate average metrics for a campaign (decimal 0.0–1.0)."""
        pipeline = [
            {"$match": {"campaign_id": campaign_id}},
            {
                "$group": {
                    "_id": "$campaign_id",
                    "avg_open_rate": {"$avg": "$open_rate"},
                    "avg_click_rate": {"$avg": "$click_rate"},
                    "avg_performance_score": {"$avg": "$performance_score"},
                    "total_sent": {"$sum": "$total_sent"},
                    "total_opens": {"$sum": "$unique_opens"},
                    "total_clicks": {"$sum": "$unique_clicks"},
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
                "total_opens": 0,
                "total_clicks": 0,
            }
        agg = results[0]
        agg.pop("_id", None)
        return agg

    async def get_performance_distribution(
        self, campaign_id: str
    ) -> list[dict[str, Any]]:
        """Return per-variant performance scores for a campaign."""
        pipeline = [
            {"$match": {"campaign_id": campaign_id}},
            {"$sort": {"performance_score": -1}},
            {
                "$project": {
                    "_id": 0,
                    "variant_id": 1,
                    "mock_campaign_id": 1,
                    "open_rate": 1,
                    "click_rate": 1,
                    "performance_score": 1,
                }
            },
        ]
        cursor = self.collection.aggregate(pipeline)
        return [doc async for doc in cursor]

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
                    "calculated_at": {"$gte": start_date, "$lte": end_date},
                }
            )
            .sort("calculated_at", 1)
        )
        return [Metrics(**doc) async for doc in cursor]
