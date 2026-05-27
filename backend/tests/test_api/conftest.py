"""Shared fixtures for API endpoint tests.

Strategy
--------
* mongomock_motor  — in-memory async MongoDB, injected via dependency override
* unittest.mock    — Mock Campaign API client (synchronous requests library)
* patch            — neutralise MongoDB.connect/disconnect/get_db so the
                     FastAPI lifespan runs without a real Mongo instance
* TestClient       — synchronous Starlette test client; background tasks run
                     inside each client.xxx() call before it returns
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

# ── Raw Mock API customer payload (18 demographic fields) ─────────────────────

MOCK_API_CUSTOMER: dict = {
    "customer_id": "CUST0001",
    "Full_name": "Ravi Sharma",
    "email": "ravi.sharma@example.com",
    "Age": 30,
    "Gender": "Male",
    "Marital_Status": "Married",
    "Family_Size": 4,
    "Dependent_count": 2,
    "Occupation": "Engineer",
    "Occupation_type": "Full-time",
    "Monthly_Income": 75000,
    "KYC_status": "Y",
    "City": "Mumbai",
    "Kids_in_Household": 1,
    "App_Installed": "Y",
    "Existing_Customer": "Y",
    "Credit_score": 720,
    "Social_Media_Active": "Y",
}

CAMPAIGN_BRIEF = (
    "Launch a Diwali sale for premium electronics targeting urban professionals "
    "aged 25–45 in Mumbai and Delhi with a ₹5 lakh budget."
)


# ── Event loop (session-scoped so async fixtures can share it) ────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── In-memory MongoDB ─────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Fresh in-memory MongoDB database per test."""
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    yield db


# ── Mock Campaign API client ──────────────────────────────────────────────────

@pytest.fixture
def mock_api_client():
    """MagicMock replacement for MockCampaignClient."""
    m = MagicMock()
    m.get_customers.return_value = [MOCK_API_CUSTOMER]
    m.get_customer_count.return_value = 5000
    m.validate_customer_ids.return_value = {
        "valid_ids": ["CUST0001"],
        "invalid_ids": [],
        "total_valid": 1,
    }
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
    m.get_campaign_results.return_value = [
        {
            "customer_id": "CUST0001",
            "opened": True,
            "clicked": False,
            "open_probability": 0.75,
            "click_probability": 0.25,
        }
    ]
    return m


# ── TestClient with all external dependencies mocked ─────────────────────────

@pytest.fixture
def client(mock_db, mock_api_client):
    """Synchronous TestClient that uses mocked DB + Mock API client.

    Dependency overrides redirect every FastAPI Depends(get_database) /
    Depends(get_mock_api_client) to in-memory / mock equivalents.
    MongoDB.get_db() direct calls (e.g. in health.py) are patched too.
    The lifespan's validate_mock_api_connection is stubbed to avoid
    60-second HTTP timeouts during test startup.
    """

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_database] = _override_db
    app.dependency_overrides[get_mock_api_client] = lambda: mock_api_client

    with ExitStack() as stack:
        # Keep get_db usable for route handlers that bypass DI (e.g. health.py)
        stack.enter_context(patch.object(MongoDB, "get_db", return_value=mock_db))
        # Skip the lifespan (no context manager) so MongoDB.connect and the
        # 60-second Mock API ping are never called during tests.
        tc = TestClient(app, raise_server_exceptions=True)
        yield tc

    app.dependency_overrides.clear()
