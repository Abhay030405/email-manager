"""Unit tests for CampaignStrategyAgent."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.strategy import CampaignStrategyAgent


def _make_agent() -> CampaignStrategyAgent:
    with patch("app.agents.base_agent.BaseAgent.setup_llm", return_value=MagicMock()):
        return CampaignStrategyAgent()


VALID_STRATEGY_RESPONSE = """{
  "selected_segments": ["young_professionals"],
  "send_schedule": {"young_professionals": "2026-05-30T10:00:00"},
  "ab_test_plan": {"num_variants": 2, "test_duration_hours": 24},
  "budget_allocation": {"young_professionals": 100.0},
  "expected_metrics": {"young_professionals": {"open_rate": 0.45, "click_rate": 0.12}},
  "reasoning": "Young professionals are the primary target with highest conversion potential."
}"""


@pytest.mark.unit
class TestCampaignStrategyAgent:

    @pytest.mark.asyncio
    async def test_strategy_returns_selected_segments(self):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_STRATEGY_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "parsed_brief": {
                "product_name": "XDeposit",
                "target_audience": "young professionals",
                "campaign_goal": "conversion",
                "budget": 50000.0,
            },
            "segments": [
                {"segment_name": "young_professionals", "customer_ids": ["CUST0001"], "size": 1}
            ],
            "current_time": datetime.utcnow().isoformat(),
        })

        assert result is not None
        assert "selected_segments" in result

    @pytest.mark.asyncio
    async def test_strategy_missing_brief_raises(self):
        agent = _make_agent()

        with pytest.raises(Exception):
            await agent.execute({"segments": [], "current_time": datetime.utcnow().isoformat()})
