"""Unit tests for MonitoringAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.monitoring import MonitoringAgent


def _make_agent() -> MonitoringAgent:
    with patch("app.agents.base_agent.BaseAgent.setup_llm", return_value=MagicMock()):
        return MonitoringAgent()


@pytest.mark.unit
class TestMonitoringAgent:

    @pytest.mark.asyncio
    async def test_monitoring_execute_returns_dict(self, sample_metrics_list):
        agent = _make_agent()

        result = await agent.execute({
            "campaign_id": "camp-001",
            "metrics": [m.model_dump() for m in sample_metrics_list],
        })

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_monitoring_without_metrics_handles_gracefully(self):
        agent = _make_agent()

        result = await agent.execute({
            "campaign_id": "camp-001",
            "metrics": [],
        })

        assert result is not None
