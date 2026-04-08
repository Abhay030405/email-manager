"""Generic base repository with reusable async CRUD operations."""

import logging
from typing import Any, Generic, Optional, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[T]):
    """
    Base repository providing generic CRUD operations for MongoDB collections.

    Subclass and set `COLLECTION`, `ID_FIELD`, and `model_class` to use.
    """

    COLLECTION: str = ""
    ID_FIELD: str = "id"

    def __init__(self, db: AsyncIOMotorDatabase, model_class: type[T]) -> None:
        if not self.COLLECTION:
            raise ValueError("COLLECTION must be set on the repository subclass")
        self.db = db
        self.collection: AsyncIOMotorCollection = db[self.COLLECTION]
        self.model_class = model_class

    # ── Create ────────────────────────────────────────────────────

    async def create(self, document: T) -> T:
        """Insert a new document. Returns the model instance."""
        doc = document.model_dump()
        try:
            await self.collection.insert_one(doc)
            logger.debug("Inserted into %s: %s", self.COLLECTION, doc.get(self.ID_FIELD))
        except Exception:
            logger.exception("Failed to insert into %s", self.COLLECTION)
            raise
        return document

    # ── Read ──────────────────────────────────────────────────────

    async def find_by_id(self, id_value: str) -> Optional[T]:
        """Find a single document by its primary key."""
        doc = await self.collection.find_one({self.ID_FIELD: id_value})
        if doc is None:
            return None
        return self.model_class(**doc)

    async def find_all(
        self,
        filter: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """Return documents matching *filter* with pagination."""
        cursor = self.collection.find(filter or {}).skip(skip).limit(limit)
        return [self.model_class(**doc) async for doc in cursor]

    # ── Update ────────────────────────────────────────────────────

    async def update(
        self, id_value: str, update_data: dict[str, Any]
    ) -> Optional[T]:
        """Update fields on a document identified by its primary key."""
        try:
            result = await self.collection.find_one_and_update(
                {self.ID_FIELD: id_value},
                {"$set": update_data},
                return_document=True,
            )
        except Exception:
            logger.exception("Failed to update %s in %s", id_value, self.COLLECTION)
            raise
        if result is None:
            return None
        return self.model_class(**result)

    # ── Delete ────────────────────────────────────────────────────

    async def delete(self, id_value: str) -> bool:
        """Delete a document by its primary key. Returns True if deleted."""
        result = await self.collection.delete_one({self.ID_FIELD: id_value})
        return result.deleted_count > 0

    # ── Count ─────────────────────────────────────────────────────

    async def count(self, filter: dict[str, Any] | None = None) -> int:
        """Count documents matching optional filter."""
        return await self.collection.count_documents(filter or {})
