"""Metrics test data fixtures (rates stored as 0.0–1.0 per Mock API convention)."""

import pytest

from app.models.metrics import Metrics


@pytest.fixture
def mock_metrics_response() -> dict:
    """Mock Campaign API metrics response (rates 0.0–1.0)."""
    return {
        "campaign_id": "mock-uuid-test-campaign",
        "total_sent": 100,
        "unique_opens": 60,
        "unique_clicks": 20,
        "open_rate": 0.6,
        "click_rate": 0.2,
        "click_through_rate": 0.3333,
        "calculated_at": "2026-04-15T10:00:00Z",
    }


@pytest.fixture
def mock_customer_results() -> list[dict]:
    """Per-customer results from Mock API."""
    return [
        {
            "campaign_id": "mock-uuid-test",
            "customer_id": "CUST0001",
            "opened": True,
            "clicked": True,
            "open_probability": 0.75,
            "click_probability": 0.45,
        },
        {
            "campaign_id": "mock-uuid-test",
            "customer_id": "CUST0002",
            "opened": True,
            "clicked": False,
            "open_probability": 0.60,
            "click_probability": 0.25,
        },
        {
            "campaign_id": "mock-uuid-test",
            "customer_id": "CUST0003",
            "opened": False,
            "clicked": False,
            "open_probability": 0.30,
            "click_probability": 0.10,
        },
    ]


@pytest.fixture
def sample_metrics() -> Metrics:
    return Metrics(
        metric_id="met-test-001",
        variant_id="var-test-001",
        campaign_id="camp-test-001",
        mock_campaign_id="mock-api-001",
        open_rate=0.35,
        click_rate=0.085,
        click_through_rate=0.06,
        total_sent=1000,
        unique_opens=350,
        unique_clicks=85,
    )


@pytest.fixture
def sample_metrics_high_performer() -> Metrics:
    return Metrics(
        metric_id="met-test-high",
        variant_id="var-test-high",
        campaign_id="camp-test-001",
        mock_campaign_id="mock-api-high",
        open_rate=0.65,
        click_rate=0.25,
        click_through_rate=0.20,
        total_sent=500,
        unique_opens=325,
        unique_clicks=125,
    )


@pytest.fixture
def sample_metrics_low_performer() -> Metrics:
    return Metrics(
        metric_id="met-test-low",
        variant_id="var-test-low",
        campaign_id="camp-test-001",
        mock_campaign_id="mock-api-low",
        open_rate=0.08,
        click_rate=0.01,
        click_through_rate=0.005,
        total_sent=500,
        unique_opens=40,
        unique_clicks=5,
    )


@pytest.fixture
def sample_metrics_list() -> list[Metrics]:
    return [
        Metrics(
            metric_id="met-test-001",
            variant_id="var-test-001",
            campaign_id="camp-test-001",
            mock_campaign_id="mock-001",
            open_rate=0.40,
            click_rate=0.10,
            click_through_rate=0.07,
            total_sent=1000,
            unique_opens=400,
            unique_clicks=100,
        ),
        Metrics(
            metric_id="met-test-002",
            variant_id="var-test-002",
            campaign_id="camp-test-001",
            mock_campaign_id="mock-002",
            open_rate=0.20,
            click_rate=0.03,
            click_through_rate=0.02,
            total_sent=800,
            unique_opens=160,
            unique_clicks=24,
        ),
        Metrics(
            metric_id="met-test-003",
            variant_id="var-test-003",
            campaign_id="camp-test-002",
            mock_campaign_id="mock-003",
            open_rate=0.50,
            click_rate=0.15,
            click_through_rate=0.10,
            total_sent=500,
            unique_opens=250,
            unique_clicks=75,
        ),
    ]
