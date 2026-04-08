"""MongoDB connection manager using Motor (async) driver."""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import get_settings
from app.models import (
    CAMPAIGN_INDEXES,
    CUSTOMER_INDEXES,
    METRICS_INDEXES,
    SEGMENT_INDEXES,
    VARIANT_INDEXES,
)

logger = logging.getLogger(__name__)


class MongoDB:
    """Singleton-style MongoDB connection manager with pooling."""

    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

    @classmethod
    async def connect(cls) -> None:
        """Establish MongoDB connection with pooling and ensure indexes."""
        settings = get_settings()
        try:
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True,
            )
            # Verify the connection is alive
            await cls.client.admin.command("ping")
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            logger.info("Connected to MongoDB: %s", settings.MONGODB_DB_NAME)
            await cls._ensure_indexes()
        except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
            cls.client = None
            cls.db = None
            logger.error("Failed to connect to MongoDB: %s", exc)
            raise RuntimeError(
                f"Could not connect to MongoDB at {settings.MONGODB_URL}"
            ) from exc

    @classmethod
    async def disconnect(cls) -> None:
        """Close the MongoDB connection and release pool resources."""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("Disconnected from MongoDB")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Return the database instance."""
        if cls.db is None:
            raise RuntimeError("MongoDB is not connected. Call connect() first.")
        return cls.db

    @classmethod
    async def _ensure_indexes(cls) -> None:
        """Create indexes for all collections."""
        db = cls.get_db()

        index_map = {
            "customers": CUSTOMER_INDEXES,
            "campaigns": CAMPAIGN_INDEXES,
            "campaign_variants": VARIANT_INDEXES,
            "metrics": METRICS_INDEXES,
            "segments": SEGMENT_INDEXES,
        }

        for collection_name, indexes in index_map.items():
            collection = db[collection_name]
            for idx in indexes:
                kwargs = {}
                if idx.get("unique"):
                    kwargs["unique"] = True
                await collection.create_index(idx["keys"], **kwargs)
                logger.info(
                    "Ensured index %s on %s", idx["keys"], collection_name
                )


def get_database() -> AsyncIOMotorDatabase:
    """Dependency helper to get database instance."""
    return MongoDB.get_db()
