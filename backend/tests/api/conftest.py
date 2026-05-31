"""Shared fixtures for tests/api/ endpoint tests.

Uses the same strategy as tests/test_api/conftest.py:
- mongomock_motor for in-memory MongoDB
- dependency_overrides to inject the mock DB
- MongoDB.get_db patched so health routes don't crash
- TestClient without a context manager (no lifespan = no real Mongo connection)
"""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.api.deps import get_database, get_mock_api_client
from app.db.mongodb import MongoDB
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    client = AsyncMongoMockClient()
    return client["campaignx_test"]


@pytest.fixture
def mock_api_client():
    m = MagicMock()
    m.get_customers.return_value = []
    m.get_customer_count.return_value = 5000
    m.validate_customer_ids.return_value = {"valid_ids": [], "invalid_ids": [], "total_valid": 0}
    m.schedule_campaign.return_value = {
        "campaign_id": "mock-api-camp-001",
        "status": "scheduled",
        "total_customers": 1,
    }
    m.get_campaign_metrics.return_value = {
        "campaign_id": "mock-api-camp-001",
        "open_rate": 0.35,
        "click_rate": 0.085,
        "click_through_rate": 0.06,
        "total_sent": 1000,
        "unique_opens": 350,
        "unique_clicks": 85,
    }
    m.get_campaign_results.return_value = []
    m.health_check.return_value = {"status": "ok", "latency_ms": 12.0}
    return m


@pytest.fixture
def client(mock_db, mock_api_client):
    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_database] = _override_db
    app.dependency_overrides[get_mock_api_client] = lambda: mock_api_client

    with ExitStack() as stack:
        stack.enter_context(patch.object(MongoDB, "get_db", return_value=mock_db))
        tc = TestClient(app, raise_server_exceptions=True)
        yield tc

    app.dependency_overrides.clear()
