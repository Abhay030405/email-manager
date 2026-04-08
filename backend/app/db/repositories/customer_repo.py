"""Repository for customer data access."""

import logging
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

    # ── Specialised queries ───────────────────────────────────────

    async def find_by_criteria(
        self,
        age_range: tuple[int, int] | None = None,
        gender: str | None = None,
        location: str | None = None,
        activity_status: str | None = None,
    ) -> list[Customer]:
        """Find customers matching demographic criteria."""
        query: dict[str, Any] = {}
        if age_range:
            query["age"] = {"$gte": age_range[0], "$lte": age_range[1]}
        if gender:
            query["gender"] = gender
        if location:
            query["location"] = location
        if activity_status:
            query["activity_status"] = activity_status
        return await self.find_all(filter=query, limit=10_000)

    async def get_active_customers(self) -> list[Customer]:
        """Return all customers with active status."""
        return await self.find_all(filter={"activity_status": "active"}, limit=10_000)

    async def bulk_insert_customers(self, customers: list[Customer]) -> bool:
        """Insert many customers at once. Returns True on success."""
        if not customers:
            return True
        docs = [c.model_dump() for c in customers]
        try:
            result = await self.collection.insert_many(docs, ordered=False)
            logger.info("Bulk inserted %d customers", len(result.inserted_ids))
            return True
        except Exception:
            logger.exception("Bulk insert failed")
            raise

    async def get_customer_count_by_segment(
        self, criteria: dict[str, Any]
    ) -> int:
        """Count customers matching segment-style filter criteria."""
        return await self.count(filter=criteria)
