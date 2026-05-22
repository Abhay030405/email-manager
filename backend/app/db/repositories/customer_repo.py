"""Repository for customer data access — Mock Campaign API-aligned fields."""

import logging
from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.repositories.base_repository import BaseRepository
from app.models.customer import Customer

logger = logging.getLogger(__name__)


class CustomerRepository(BaseRepository[Customer]):
    """Data access layer for the customers collection."""

    COLLECTION = "customers"
    ID_FIELD = "customer_id"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db, Customer)

    # ── Mock API Sync ─────────────────────────────────────────────

    async def sync_from_mock_api(self, customers: list[Customer]) -> int:
        """Upsert customers fetched from the Mock API.

        Returns the number of upserted documents.
        """
        if not customers:
            return 0
        count = 0
        for c in customers:
            doc = c.model_dump()
            doc["synced_from_mock_api"] = True
            doc["last_synced_at"] = datetime.utcnow()
            result = await self.collection.update_one(
                {"customer_id": c.customer_id},
                {"$set": doc},
                upsert=True,
            )
            if result.upserted_id or result.modified_count:
                count += 1
        logger.info("Synced %d customers from Mock API", count)
        return count

    async def get_synced_customer_count(self) -> int:
        """Count customers synced from the Mock API."""
        return await self.count(filter={"synced_from_mock_api": True})

    # ── Specialised queries (Mock API fields) ─────────────────────

    async def find_by_criteria(
        self,
        age_range: tuple[int, int] | None = None,
        gender: str | None = None,
        city: str | None = None,
        cities: list[str] | None = None,
        marital_status: str | None = None,
        occupation_type: str | None = None,
        min_income: float | None = None,
        max_income: float | None = None,
        credit_score_range: tuple[int, int] | None = None,
        app_installed: str | None = None,
        social_media_active: str | None = None,
        existing_customer: str | None = None,
    ) -> list[Customer]:
        """Find customers matching demographic criteria (Mock API fields)."""
        query: dict[str, Any] = {}
        if age_range:
            query["Age"] = {"$gte": age_range[0], "$lte": age_range[1]}
        if gender:
            query["Gender"] = gender
        if city:
            query["City"] = city
        if cities:
            query["City"] = {"$in": cities}
        if marital_status:
            query["Marital_Status"] = marital_status
        if occupation_type:
            query["Occupation_type"] = occupation_type
        if min_income is not None or max_income is not None:
            income_q: dict[str, Any] = {}
            if min_income is not None:
                income_q["$gte"] = min_income
            if max_income is not None:
                income_q["$lte"] = max_income
            query["Monthly_Income"] = income_q
        if credit_score_range:
            query["Credit_score"] = {
                "$gte": credit_score_range[0],
                "$lte": credit_score_range[1],
            }
        if app_installed:
            query["App_Installed"] = app_installed
        if social_media_active:
            query["Social_Media_Active"] = social_media_active
        if existing_customer:
            query["Existing_Customer"] = existing_customer
        return await self.find_all(filter=query, limit=10_000)

    async def validate_customer_ids(self, customer_ids: list[str]) -> list[str]:
        """Return the subset of customer_ids that exist in the database."""
        cursor = self.collection.find(
            {"customer_id": {"$in": customer_ids}},
            {"customer_id": 1},
        )
        return [doc["customer_id"] async for doc in cursor]

    async def get_customer_count_by_segment(
        self, criteria: dict[str, Any]
    ) -> int:
        """Count customers matching segment-style filter criteria."""
        return await self.count(filter=criteria)
