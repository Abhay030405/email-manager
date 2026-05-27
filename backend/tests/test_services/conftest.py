"""Shared fixtures for service-layer tests."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.db.repositories.analytics_repo import AnalyticsRepository
from app.db.repositories.metric_aggregation_repo import MetricAggregationRepository
from app.db.repositories.metrics_repo import MetricsRepository
from app.db.repositories.performance_alert_repo import PerformanceAlertRepository
from app.models.metrics import Metrics


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
def metrics_repo(mock_db):
    return MetricsRepository(mock_db)


@pytest.fixture
def alert_repo(mock_db):
    return PerformanceAlertRepository(mock_db)


@pytest.fixture
def analytics_repo(mock_db):
    return AnalyticsRepository(mock_db)


@pytest.fixture
def aggregation_repo(mock_db):
    return MetricAggregationRepository(mock_db)


def make_metrics(
    campaign_id: str = "camp-001",
    variant_id: str = "var-001",
    mock_campaign_id: str = "mock-001",
    open_rate: float = 0.35,
    click_rate: float = 0.08,
    click_through_rate: float = 0.06,
    total_sent: int = 1000,
    unique_opens: int = 350,
    unique_clicks: int = 80,
    collected_at: datetime | None = None,
) -> Metrics:
    return Metrics(
        variant_id=variant_id,
        campaign_id=campaign_id,
        mock_campaign_id=mock_campaign_id,
        open_rate=open_rate,
        click_rate=click_rate,
        click_through_rate=click_through_rate,
        total_sent=total_sent,
        unique_opens=unique_opens,
        unique_clicks=unique_clicks,
        collected_at=collected_at or datetime.utcnow(),  # noqa: DTZ003
    )


def make_mock_api_client(
    open_rate: float = 0.35,
    click_rate: float = 0.08,
    ctr: float = 0.06,
    total_sent: int = 1000,
    unique_opens: int = 350,
    unique_clicks: int = 80,
) -> MagicMock:
    m = MagicMock()
    m.get_campaign_metrics.return_value = {
        "campaign_id": "mock-001",
        "open_rate": open_rate,
        "click_rate": click_rate,
        "click_through_rate": ctr,
        "total_sent": total_sent,
        "unique_opens": unique_opens,
        "unique_clicks": unique_clicks,
    }
    m.get_campaign_results.return_value = []
    return m
