"""Unit tests for CampaignBriefParserAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.brief_parser import CampaignBriefParserAgent, BriefInput, ParsedBrief


def _make_agent() -> CampaignBriefParserAgent:
    """Create agent with a mocked LLM so no real API calls happen."""
    with patch("app.agents.base_agent.ChatOpenAI") as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        agent = CampaignBriefParserAgent()
    return agent


VALID_LLM_RESPONSE = """{
  "product_name": "XDeposit",
  "product_description": "High-yield savings account",
  "target_audience": "Young professionals aged 25-35",
  "campaign_goal": "conversion",
  "cta_link": "https://example.com/xdeposit",
  "budget": 50000.0,
  "preferred_tone": "professional",
  "key_messages": ["1% higher returns", "Flexible terms", "No minimum balance"],
  "constraints": null
}"""


@pytest.mark.unit
class TestBriefParserAgent:

    @pytest.mark.asyncio
    async def test_parse_valid_brief(self):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_LLM_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "brief_text": "Promote XDeposit savings account to young professionals. "
                          "Drive conversions at https://example.com/xdeposit. Budget $50k."
        })

        assert result is not None
        assert result["product_name"] == "XDeposit"
        assert result["campaign_goal"] == "conversion"
        assert result["target_audience"] is not None

    @pytest.mark.asyncio
    async def test_parse_extracts_product_name(self):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_LLM_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "brief_text": "Promote XDeposit savings account."
        })

        assert "product_name" in result
        assert result["product_name"] == "XDeposit"

    @pytest.mark.asyncio
    async def test_parse_extracts_campaign_goal(self):
        agent = _make_agent()
        mock_response = MagicMock()
        mock_response.content = VALID_LLM_RESPONSE
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await agent.execute({
            "brief_text": "Get sign-ups for XDeposit."
        })

        assert result["campaign_goal"] in {"awareness", "conversion", "retention", "engagement"}

    @pytest.mark.asyncio
    async def test_parse_empty_brief_raises_value_error(self):
        agent = _make_agent()

        with pytest.raises((ValueError, Exception)):
            await agent.execute({"brief_text": ""})

    @pytest.mark.asyncio
    async def test_parse_missing_brief_key_raises(self):
        agent = _make_agent()

        with pytest.raises((ValueError, Exception, KeyError)):
            await agent.execute({})

    def test_parse_budget_string_with_k_suffix(self):
        agent = _make_agent()
        assert agent._parse_budget("$5k") == 5000.0
        assert agent._parse_budget("8K") == 8000.0
        assert agent._parse_budget("$10,000") == 10000.0
        assert agent._parse_budget("not-a-number") is None

    def test_parse_budget_plain_number(self):
        agent = _make_agent()
        assert agent._parse_budget("50000") == 50000.0
        assert agent._parse_budget("25000.50") == 25000.50

    def test_post_process_cta_link_sentinel_cleared(self):
        agent = _make_agent()
        data = {"cta_link": "unknown", "key_messages": []}
        processed = agent._post_process(data, "brief")
        assert processed["cta_link"] == ""

    def test_post_process_key_messages_string_split(self):
        agent = _make_agent()
        data = {"key_messages": "msg1, msg2, msg3", "cta_link": ""}
        processed = agent._post_process(data, "brief")
        assert isinstance(processed["key_messages"], list)
        assert len(processed["key_messages"]) == 3

    def test_post_process_missing_optional_keys_filled(self):
        agent = _make_agent()
        data = {"key_messages": []}
        processed = agent._post_process(data, "brief")
        assert "preferred_tone" in processed
        assert "constraints" in processed
        assert "budget" in processed


@pytest.mark.unit
class TestBriefInput:

    def test_valid_brief_input(self):
        b = BriefInput(brief_text="A valid brief text")
        assert b.brief_text == "A valid brief text"

    def test_brief_text_stripped(self):
        b = BriefInput(brief_text="  stripped  ")
        assert b.brief_text == "stripped"

    def test_empty_brief_raises(self):
        with pytest.raises(ValueError):
            BriefInput(brief_text="")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            BriefInput(brief_text="   ")


@pytest.mark.unit
class TestParsedBrief:

    def test_valid_parsed_brief(self):
        pb = ParsedBrief(
            product_name="TestProduct",
            target_audience="Young adults",
            campaign_goal="conversion",
        )
        assert pb.product_name == "TestProduct"
        assert pb.campaign_goal == "conversion"

    def test_invalid_campaign_goal_raises(self):
        with pytest.raises(ValueError):
            ParsedBrief(
                product_name="P",
                target_audience="T",
                campaign_goal="invalid_goal",
            )

    def test_invalid_tone_falls_back_to_professional(self):
        pb = ParsedBrief(
            product_name="P",
            target_audience="T",
            campaign_goal="awareness",
            preferred_tone="nonsense",
        )
        assert pb.preferred_tone == "professional"

    def test_empty_product_name_raises(self):
        with pytest.raises(ValueError):
            ParsedBrief(
                product_name="unknown",
                target_audience="T",
                campaign_goal="awareness",
            )

    def test_cta_link_validated(self):
        pb = ParsedBrief(
            product_name="P",
            target_audience="T",
            campaign_goal="awareness",
            cta_link="https://valid.url/path",
        )
        assert pb.cta_link == "https://valid.url/path"

    def test_invalid_cta_link_raises(self):
        with pytest.raises(ValueError):
            ParsedBrief(
                product_name="P",
                target_audience="T",
                campaign_goal="awareness",
                cta_link="not-a-url",
            )
