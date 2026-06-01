"""Unit tests for ExecutionAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.execution import ExecutionAgent


def _make_agent() -> ExecutionAgent:
    with patch("app.agents.base_agent.BaseAgent.setup_llm", return_value=MagicMock()):
        return ExecutionAgent()


@pytest.mark.unit
class TestExecutionAgent:

    @pytest.mark.asyncio
    async def test_execute_with_mock_api_returns_result(self, sample_variants, mock_campaign_client):
        agent = _make_agent()

        result = await agent.execute({
            "campaign_id": "camp-test-001",
            "variants": [v.model_dump() for v in sample_variants],
            "mock_api_client": mock_campaign_client,
        })

        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_missing_campaign_id_raises(self):
        agent = _make_agent()

        with pytest.raises(Exception):
            await agent.execute({"variants": []})
