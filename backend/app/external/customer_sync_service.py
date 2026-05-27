"""Customer synchronisation service — pages through Mock API and caches results."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.external.mock_campaign_client import MockCampaignClient, MockCampaignAPIError

logger = logging.getLogger(__name__)

_DEFAULT_PAGE_SIZE = 100
_MAX_CUSTOMERS = 5000


class CustomerSyncService:
    """Fetches all customers from the Mock API using paginated requests.

    Results are cached in-memory so repeated calls within a session avoid
    redundant network round-trips.  Call ``refresh_cache()`` to force a
    fresh sync.
    """

    def __init__(
        self,
        client: MockCampaignClient | None = None,
        page_size: int = _DEFAULT_PAGE_SIZE,
    ) -> None:
        self._client = client or MockCampaignClient()
        self._page_size = page_size
        self._cache: list[dict[str, Any]] = []
        self._cache_synced_at: datetime | None = None
        self._total_available: int = 0

    # ── Public API ─────────────────────────────────────────────────────────

    async def sync_all_customers(self) -> dict[str, Any]:
        """Fetch all customers from the Mock API, page by page.

        Returns:
            Dict with ``customers``, ``total_synced``, ``total_available``,
            and ``synced_at`` keys.
        """
        if self._cache:
            logger.info("Returning %d cached customers", len(self._cache))
            return self._build_result()

        return await self._do_sync()

    async def refresh_cache(self) -> dict[str, Any]:
        """Discard cached data and re-sync all customers from the Mock API."""
        self._cache = []
        self._cache_synced_at = None
        return await self._do_sync()

    def get_cache_stats(self) -> dict[str, Any]:
        """Return metadata about the current in-memory cache."""
        return {
            "cached": len(self._cache) > 0,
            "total_cached": len(self._cache),
            "total_available": self._total_available,
            "synced_at": self._cache_synced_at.isoformat() if self._cache_synced_at else None,
        }

    def get_customer_ids(self) -> list[str]:
        """Return the list of customer_id strings from the cache."""
        return [c.get("customer_id", "") for c in self._cache if c.get("customer_id")]

    # ── Internal ───────────────────────────────────────────────────────────

    async def _do_sync(self) -> dict[str, Any]:
        loop = asyncio.get_event_loop()

        # Discover total count first
        try:
            total = await loop.run_in_executor(
                None, self._client.get_customer_count
            )
            self._total_available = min(total, _MAX_CUSTOMERS)
        except Exception as exc:
            logger.warning("Could not fetch customer count: %s — defaulting to %d", exc, _MAX_CUSTOMERS)
            self._total_available = _MAX_CUSTOMERS

        all_customers: list[dict[str, Any]] = []
        offset = 0
        pages_fetched = 0

        while offset < self._total_available:
            limit = min(self._page_size, self._total_available - offset)
            try:
                page = await loop.run_in_executor(
                    None,
                    lambda o=offset, l=limit: self._client.get_customers(limit=l, offset=o),
                )
                if not page:
                    logger.info("Empty page at offset %d — stopping pagination", offset)
                    break

                # Validate each record; skip malformed ones
                for customer in page:
                    try:
                        self._client._validate_customer_data(customer)
                        all_customers.append(customer)
                    except ValueError as exc:
                        logger.warning("Skipping malformed customer record: %s", exc)

                pages_fetched += 1
                offset += len(page)
                logger.debug("Synced page %d: %d customers (total so far: %d)", pages_fetched, len(page), len(all_customers))

                if len(page) < limit:
                    break

            except MockCampaignAPIError as exc:
                logger.error("Mock API error during customer sync at offset %d: %s", offset, exc)
                break
            except Exception as exc:
                logger.error("Unexpected error during customer sync at offset %d: %s", offset, exc)
                break

        self._cache = all_customers
        self._cache_synced_at = datetime.now(tz=timezone.utc)
        logger.info(
            "Customer sync complete: %d/%d customers fetched in %d pages",
            len(all_customers),
            self._total_available,
            pages_fetched,
        )
        return self._build_result()

    def _build_result(self) -> dict[str, Any]:
        return {
            "customers": self._cache,
            "total_synced": len(self._cache),
            "total_available": self._total_available,
            "synced_at": self._cache_synced_at.isoformat() if self._cache_synced_at else None,
        }
