"""Unit tests for OptimizationService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient

from app.services.optimization_service import OptimizationService


@pytest_asyncio.fixture
async def optimization_service():
    client = AsyncMongoMockClient()
    db = client["campaignx_test"]
    mock_api_client = MagicMock()
    service = OptimizationService(db=db, mock_api_client=mock_api_client)
    yield service
    client.close()


@pytest.mark.unit
class TestOptimizationService:

    @pytest.mark.asyncio
    async def test_analyze_returns_opportunity(self, optimization_service, sample_metrics_list):
        result = await optimization_service.analyze_opportunity(
            campaign_id="camp-001",
            metrics=sample_metrics_list,
        )
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_analyze_empty_metrics(self, optimization_service):
        result = await optimization_service.analyze_opportunity(
            campaign_id="camp-001",
            metrics=[],
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_optimization_history(self, optimization_service):
        history = await optimization_service.get_optimization_history("camp-001")
        assert isinstance(history, list)
