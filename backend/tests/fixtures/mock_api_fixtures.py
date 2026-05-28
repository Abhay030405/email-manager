"""Mock Campaign API response fixtures."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_api_health_response() -> dict:
    return {
        "status": "healthy",
        "customers_loaded": 5000,
        "version": "1.0.0",
    }


@pytest.fixture
def mock_api_customer_count_response() -> dict:
    return {"count": 5000, "total": 5000}


@pytest.fixture
def mock_api_validate_response() -> dict:
    return {
        "valid_ids": ["CUST0001", "CUST0002"],
        "invalid_ids": [],
        "total_valid": 2,
    }


@pytest.fixture
def mock_api_validate_response_with_invalid() -> dict:
    return {
        "valid_ids": ["CUST0001"],
        "invalid_ids": ["FAKE_ID"],
        "total_valid": 1,
    }


@pytest.fixture
def mock_api_schedule_response() -> dict:
    return {
        "campaign_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "scheduled",
        "total_customers": 100,
        "scheduled_time": "2026-04-15T10:00:00Z",
    }


@pytest.fixture
def mock_api_metrics_response() -> dict:
    return {
        "campaign_id": "550e8400-e29b-41d4-a716-446655440000",
        "open_rate": 0.35,
        "click_rate": 0.085,
        "click_through_rate": 0.06,
        "total_sent": 1000,
        "unique_opens": 350,
        "unique_clicks": 85,
    }


@pytest.fixture
def mock_api_results_response() -> list[dict]:
    return [
        {
            "customer_id": "CUST0001",
            "opened": True,
            "clicked": False,
            "open_probability": 0.75,
            "click_probability": 0.25,
        },
        {
            "customer_id": "CUST0002",
            "opened": False,
            "clicked": False,
            "open_probability": 0.20,
            "click_probability": 0.05,
        },
    ]


@pytest.fixture
def mock_campaign_client(
    mock_api_schedule_response,
    mock_api_metrics_response,
    mock_api_results_response,
    mock_api_validate_response,
) -> MagicMock:
    """Fully wired MagicMock for MockCampaignClient."""
    from app.external.mock_campaign_client import MockCampaignClient

    client = MagicMock(spec=MockCampaignClient)
    client.get_customer_count.return_value = 5000
    client.get_customers.return_value = []
    client.validate_customer_ids.return_value = mock_api_validate_response
    client.schedule_campaign.return_value = mock_api_schedule_response
    client.get_campaign_metrics.return_value = mock_api_metrics_response
    client.get_campaign_results.return_value = mock_api_results_response
    client.health_check.return_value = {"status": "ok", "latency_ms": 45.0}
    return client
