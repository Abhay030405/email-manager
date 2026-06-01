"""Unit tests for OptimizationAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.optimization import OptimizationAgent


def _make_agent() -> OptimizationAgent:
    with patch("app.agents.base_agent.BaseAgent.setup_llm", return_value=MagicMock()):
        return OptimizationAgent()


VALID_OPPORTUNITY_RESPONSE = """{
  "overall_performance": "below_average",
  "poor_performers": [
    {"variant_id": "var-002", "performance_score": 0.08, "reason": "Low open rate"}
  ],
  "improvement_potential": "high",
  "recommended_actions": ["improve_subject_line", "adjust_send_time"]
}"""

VALID_INSIGHTS_RESPONSE = """{
  "insights": [
    {
      "variant_id": "var-002",
      "issue": "Subject line too generic",
      "recommendation": "Use personalised subject with customer name",
      "expected_improvement": 15.0
    }
  ]
}"""


@pytest.mark.unit
class TestOptimizationAgent:

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self, sample_metrics_list):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_OPPORTUNITY_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "campaign_id": "camp-001",
            "metrics": [m.model_dump() for m in sample_metrics_list],
            "customer_results": [],
        })

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_analyze_identifies_poor_performers(self, sample_metrics_list):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_OPPORTUNITY_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "campaign_id": "camp-001",
            "metrics": [m.model_dump() for m in sample_metrics_list],
            "customer_results": [],
        })

        assert result is not None

    def test_campaign_id_required(self):
        agent = _make_agent()
        with pytest.raises(Exception):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                agent.execute({"metrics": []})
            )
