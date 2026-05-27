"""Tests for CustomerSyncService — uses MagicMock to avoid HTTP."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from app.external.customer_sync_service import CustomerSyncService
from app.external.mock_campaign_client import MockCampaignAPIError


def _make_customers(n: int, start: int = 0) -> list[dict]:
    return [{"customer_id": f"CUST{i:04d}", "email": f"u{i}@x.com"} for i in range(start, start + n)]


def _make_client(count: int = 200, page_size: int = 100) -> MagicMock:
    client = MagicMock()
    client.get_customer_count.return_value = count

    def _get_customers(limit: int = 100, offset: int = 0):
        batch = _make_customers(min(limit, max(0, count - offset)), start=offset)
        return batch

    client.get_customers.side_effect = _get_customers
    client._validate_customer_data = MagicMock()  # no-op by default
    return client


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── sync_all_customers ────────────────────────────────────────────────────────

def test_sync_all_customers_fetches_all():
    client = _make_client(count=250, page_size=100)
    svc = CustomerSyncService(client=client, page_size=100)
    result = run(svc.sync_all_customers())
    assert result["total_synced"] == 250
    assert len(result["customers"]) == 250


def test_sync_all_customers_uses_cache_on_second_call():
    client = _make_client(count=50)
    svc = CustomerSyncService(client=client, page_size=100)
    run(svc.sync_all_customers())
    run(svc.sync_all_customers())
    # get_customers called only once (first sync)
    assert client.get_customers.call_count == 1


def test_sync_all_customers_partial_page_stops_early():
    client = MagicMock()
    client.get_customer_count.return_value = 1000
    # Return 50 on first call, empty on second
    client.get_customers.side_effect = [_make_customers(50), []]
    client._validate_customer_data = MagicMock()
    svc = CustomerSyncService(client=client, page_size=100)
    result = run(svc.sync_all_customers())
    assert result["total_synced"] == 50


def test_sync_stops_on_api_error():
    client = MagicMock()
    client.get_customer_count.return_value = 500
    client.get_customers.side_effect = MockCampaignAPIError(500, "server error")
    client._validate_customer_data = MagicMock()
    svc = CustomerSyncService(client=client, page_size=100)
    result = run(svc.sync_all_customers())
    assert result["total_synced"] == 0


def test_sync_skips_malformed_customers():
    client = MagicMock()
    client.get_customer_count.return_value = 2
    good = {"customer_id": "CUST0001"}
    bad = {"email": "no-id@x.com"}  # missing customer_id
    client.get_customers.return_value = [good, bad]

    from app.external.mock_campaign_client import MockCampaignClient

    def _validate(c):
        MockCampaignClient._validate_customer_data(c)

    client._validate_customer_data.side_effect = _validate
    svc = CustomerSyncService(client=client, page_size=100)
    result = run(svc.sync_all_customers())
    # bad record skipped
    assert result["total_synced"] == 1


# ── refresh_cache ─────────────────────────────────────────────────────────────

def test_refresh_cache_re_fetches():
    client = _make_client(count=10)
    svc = CustomerSyncService(client=client, page_size=100)
    run(svc.sync_all_customers())
    run(svc.refresh_cache())
    assert client.get_customers.call_count == 2


# ── get_cache_stats ───────────────────────────────────────────────────────────

def test_cache_stats_before_sync():
    svc = CustomerSyncService(client=MagicMock())
    stats = svc.get_cache_stats()
    assert stats["cached"] is False
    assert stats["total_cached"] == 0
    assert stats["synced_at"] is None


def test_cache_stats_after_sync():
    client = _make_client(count=5)
    svc = CustomerSyncService(client=client, page_size=100)
    run(svc.sync_all_customers())
    stats = svc.get_cache_stats()
    assert stats["cached"] is True
    assert stats["total_cached"] == 5
    assert stats["synced_at"] is not None


# ── get_customer_ids ──────────────────────────────────────────────────────────

def test_get_customer_ids_after_sync():
    client = _make_client(count=3)
    svc = CustomerSyncService(client=client, page_size=100)
    run(svc.sync_all_customers())
    ids = svc.get_customer_ids()
    assert len(ids) == 3
    assert all(cid.startswith("CUST") for cid in ids)


def test_get_customer_ids_empty_before_sync():
    svc = CustomerSyncService(client=MagicMock())
    assert svc.get_customer_ids() == []
