"""Shared fixtures for error_handling/ tests that test API endpoints."""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

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
    m.health_check.return_value = {"status": "ok", "latency_ms": 5.0}
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
