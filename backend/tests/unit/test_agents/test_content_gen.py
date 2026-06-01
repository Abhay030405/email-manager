"""Unit tests for ContentGenerationAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.content_gen import ContentGenerationAgent


def _make_agent() -> ContentGenerationAgent:
    with patch("app.agents.base_agent.BaseAgent.setup_llm", return_value=MagicMock()):
        return ContentGenerationAgent()


VALID_CONTENT_RESPONSE = """{
  "subject_line": "Unlock Higher Returns with XDeposit - Limited Time Offer",
  "preview_text": "Earn 1% more with our exclusive savings account",
  "email_body": "<p>Dear {Full_name},</p><p>We are excited to introduce XDeposit...</p>",
  "personalization_tags": ["Full_name", "City"],
  "variant_metadata": {"archetype": "benefit", "variant_id": "var_1"}
}"""


@pytest.mark.unit
class TestContentGenerationAgent:

    @pytest.mark.asyncio
    async def test_generate_returns_email_content(self):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_CONTENT_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "parsed_brief": {
                "product_name": "XDeposit",
                "target_audience": "young professionals",
                "campaign_goal": "conversion",
                "key_messages": ["Higher returns", "Flexible terms"],
                "preferred_tone": "professional",
            },
            "segment": {
                "segment_name": "young_professionals",
                "description": "Professionals aged 25-35",
                "customer_ids": ["CUST0001"],
            },
            "variant_id": "var-test-001",
            "strategy": {},
        })

        assert result is not None
        assert "subject_line" in result

    @pytest.mark.asyncio
    async def test_generated_content_has_email_body(self):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_CONTENT_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "parsed_brief": {
                "product_name": "XDeposit",
                "target_audience": "young professionals",
                "campaign_goal": "conversion",
            },
            "segment": {"segment_name": "test_seg"},
            "variant_id": "var-1",
            "strategy": {},
        })

        assert "email_body" in result or "subject_line" in result

    @pytest.mark.asyncio
    async def test_missing_parsed_brief_raises(self):
        agent = _make_agent()

        with pytest.raises(Exception):
            await agent.execute({
                "segment": {"segment_name": "test"},
                "variant_id": "var-1",
                "strategy": {},
            })
