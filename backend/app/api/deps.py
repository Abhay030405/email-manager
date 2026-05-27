"""FastAPI dependency providers for database, repositories, and pagination."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.db.mongodb import MongoDB
from app.db.repositories.campaign_repo import CampaignRepository
from app.db.repositories.customer_repo import CustomerRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.segment_repo import SegmentRepository
from app.db.repositories.variant_repo import VariantRepository
from app.external.mock_campaign_client import MockCampaignClient


# ── Database ──────────────────────────────────────────────────────

async def get_database() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Yield the MongoDB database instance (async generator for clean lifecycle)."""
    yield MongoDB.get_db()


def get_db() -> AsyncIOMotorDatabase:
    """Synchronous shorthand — identical result, no yield overhead."""
    return MongoDB.get_db()


DBDep = Annotated[AsyncIOMotorDatabase, Depends(get_database)]


# ── Repositories ──────────────────────────────────────────────────

def get_campaign_repo(db: DBDep) -> CampaignRepository:
    return CampaignRepository(db)


def get_customer_repo(db: DBDep) -> CustomerRepository:
    return CustomerRepository(db)


def get_variant_repo(db: DBDep) -> VariantRepository:
    return VariantRepository(db)


def get_metrics_repo(db: DBDep) -> MetricsRepository:
    return MetricsRepository(db)


def get_segment_repo(db: DBDep) -> SegmentRepository:
    return SegmentRepository(db)


CampaignRepoDep = Annotated[CampaignRepository, Depends(get_campaign_repo)]
CustomerRepoDep = Annotated[CustomerRepository, Depends(get_customer_repo)]
VariantRepoDep = Annotated[VariantRepository, Depends(get_variant_repo)]
MetricsRepoDep = Annotated[MetricsRepository, Depends(get_metrics_repo)]
SegmentRepoDep = Annotated[SegmentRepository, Depends(get_segment_repo)]


# ── External Client ───────────────────────────────────────────────

def get_mock_api_client() -> MockCampaignClient:
    """Return a configured Mock Campaign API client (settings-driven)."""
    settings = get_settings()
    return MockCampaignClient(
        base_url=settings.MOCK_CAMPAIGN_API_URL,
        timeout=settings.MOCK_API_TIMEOUT,
    )


# Canonical name + backward-compat alias
get_mock_client = get_mock_api_client

MockClientDep = Annotated[MockCampaignClient, Depends(get_mock_api_client)]


# ── Pagination ────────────────────────────────────────────────────

class PageParams:
    """Basic skip/limit pagination — max 200 records per page."""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    ) -> None:
        self.skip = skip
        self.limit = limit


class PaginationParams:
    """Pagination with a higher cap (1 000) for bulk / admin endpoints."""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Max records to return (hard cap 1 000)"),
    ) -> None:
        self.skip = skip
        self.limit = min(limit, 1000)


PageDep = Annotated[PageParams, Depends(PageParams)]
PaginationDep = Annotated[PaginationParams, Depends(PaginationParams)]


# ── Common query parameters ────────────────────────────────────────

class CommonQueryParams:
    """Bundle of query params shared by sortable list endpoints."""

    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
        sort_by: str = Query("created_at", pattern=r"^[a-zA-Z_]+$", description="Field to sort by"),
        sort_order: str = Query("desc", pattern=r"^(asc|desc)$", description="Sort direction"),
    ) -> None:
        self.skip = skip
        self.limit = min(limit, 1000)
        self.sort_by = sort_by
        self.sort_order = sort_order

    @property
    def mongo_sort(self) -> list[tuple[str, int]]:
        """Return Motor-compatible sort list, e.g. [("created_at", -1)]."""
        direction = -1 if self.sort_order == "desc" else 1
        return [(self.sort_by, direction)]


CommonQueryDep = Annotated[CommonQueryParams, Depends(CommonQueryParams)]
