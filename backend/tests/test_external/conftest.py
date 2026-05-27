"""Fixtures for test_external — mirrors test_api/conftest to avoid pytest_plugins duplication."""

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


@pytest.fixture
def mock_db_ext():
    client = AsyncMongoMockClient()
    db = client["campaignx_test_ext"]
    yield db


@pytest.fixture
def mock_api_client_ext():
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


@pytest.fixture
def client(mock_db_ext, mock_api_client_ext):
    """Synchronous TestClient with mocked DB and Mock API (execution tests)."""

    async def _override_db():
        yield mock_db_ext

    app.dependency_overrides[get_database] = _override_db
    app.dependency_overrides[get_mock_api_client] = lambda: mock_api_client_ext

    with ExitStack() as stack:
        stack.enter_context(patch.object(MongoDB, "get_db", return_value=mock_db_ext))
        tc = TestClient(app, raise_server_exceptions=True)
        yield tc

    app.dependency_overrides.clear()
