"""Unit tests for CustomerSegmentationAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.segmentation import CustomerSegmentationAgent


def _make_agent() -> CustomerSegmentationAgent:
    with patch("app.agents.base_agent.ChatOpenAI") as mock_llm_cls:
        mock_llm_cls.return_value = MagicMock()
        return CustomerSegmentationAgent()


VALID_SEGMENTATION_RESPONSE = """{
  "segments": [
    {
      "segment_name": "young_professionals",
      "description": "Young working professionals",
      "customer_ids": ["CUST0001", "CUST0002"],
      "size": 2,
      "priority": 1
    },
    {
      "segment_name": "seniors",
      "description": "Senior citizens",
      "customer_ids": ["CUST0004"],
      "size": 1,
      "priority": 2
    }
  ],
  "total_customers": 3,
  "coverage_pct": 100.0,
  "distribution": {"young_professionals": 66.7, "seniors": 33.3}
}"""


@pytest.mark.unit
class TestSegmentationAgent:

    @pytest.mark.asyncio
    async def test_segment_customers_returns_segments(self, sample_customers_small):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_SEGMENTATION_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "customers": [c.model_dump() for c in sample_customers_small[:3]],
            "target_audience": "young professionals",
            "campaign_goal": "conversion",
        })

        assert result is not None
        assert "segments" in result

    @pytest.mark.asyncio
    async def test_segment_result_has_required_keys(self, sample_customers_small):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_SEGMENTATION_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "customers": [c.model_dump() for c in sample_customers_small[:3]],
            "target_audience": "young professionals",
            "campaign_goal": "conversion",
        })

        assert "segments" in result
        assert "total_customers" in result

    @pytest.mark.asyncio
    async def test_empty_customers_raises(self):
        agent = _make_agent()

        with pytest.raises(Exception):
            await agent.execute({
                "customers": [],
                "target_audience": "anyone",
                "campaign_goal": "awareness",
            })

    def test_build_candidate_groups_young_professionals(self, sample_customers_small):
        agent = _make_agent()
        customers_dicts = [c.model_dump() for c in sample_customers_small]
        groups = agent._build_candidate_groups(customers_dicts, "conversion")
        assert isinstance(groups, dict)
        assert len(groups) > 0

    def test_ensure_coverage_assigns_all_customers(self, sample_customers_small):
        agent = _make_agent()
        customers_dicts = [c.model_dump() for c in sample_customers_small]
        all_ids = [c.customer_id for c in sample_customers_small]
        segments = [
            {"segment_name": "group_a", "customer_ids": all_ids[:5], "size": 5},
        ]
        result = agent._ensure_coverage(segments, customers_dicts, len(all_ids))
        covered = set()
        for seg in result:
            covered.update(seg["customer_ids"])
        assert len(covered) == len(all_ids)
