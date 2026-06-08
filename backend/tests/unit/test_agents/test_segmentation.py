"""Unit tests for CustomerSegmentationAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.segmentation import CustomerSegmentationAgent


def _make_agent() -> CustomerSegmentationAgent:
    with patch("app.agents.base_agent.BaseAgent.setup_llm", return_value=MagicMock()):
        return CustomerSegmentationAgent()


SAMPLE_TARGET_AUDIENCE = {
    "Group 1": {
        "min_age": 25,
        "max_age": 40,
        "gender": "Male",
        "KYC_status": "Y",
    }
}

SAMPLE_FILTER_RESULT = {"count": 50, "customer_ids": [f"CUST{i:04d}" for i in range(50)]}


@pytest.mark.unit
class TestSegmentationAgent:

    @pytest.mark.asyncio
    async def test_execute_returns_segments(self):
        agent = _make_agent()

        with patch.object(agent, "_call_filter", new=AsyncMock(return_value=SAMPLE_FILTER_RESULT)):
            result = await agent.execute({
                "target_audience": SAMPLE_TARGET_AUDIENCE,
                "campaign_goal": "conversion",
            })

        assert result is not None
        assert "segments" in result

    @pytest.mark.asyncio
    async def test_execute_result_has_required_keys(self):
        agent = _make_agent()

        with patch.object(agent, "_call_filter", new=AsyncMock(return_value=SAMPLE_FILTER_RESULT)):
            result = await agent.execute({
                "target_audience": SAMPLE_TARGET_AUDIENCE,
                "campaign_goal": "conversion",
            })

        assert "segments" in result
        assert "total_customers" in result
        assert "coverage_pct" in result

    @pytest.mark.asyncio
    async def test_execute_empty_target_audience_returns_general(self):
        agent = _make_agent()

        with patch.object(agent, "_call_filter", new=AsyncMock(return_value={"count": 0, "customer_ids": []})):
            result = await agent.execute({
                "target_audience": {},
                "campaign_goal": "awareness",
            })

        assert "segments" in result

    @pytest.mark.asyncio
    async def test_execute_creates_sub_segments(self):
        agent = _make_agent()

        active_result = {"count": 20, "customer_ids": [f"CUST00{i:02d}" for i in range(20)]}
        inactive_result = {"count": 15, "customer_ids": [f"CUST01{i:02d}" for i in range(15)]}
        dormant_result = {"count": 30, "customer_ids": [f"CUST02{i:02d}" for i in range(30)]}

        with patch.object(
            agent,
            "_call_filter",
            new=AsyncMock(side_effect=[active_result, inactive_result, dormant_result]),
        ):
            result = await agent.execute({
                "target_audience": SAMPLE_TARGET_AUDIENCE,
                "campaign_goal": "engagement",
            })

        assert len(result["segments"]) >= 1

    def test_build_filter_body_maps_fields_correctly(self):
        from app.agents.segmentation import _build_filter_body

        group = {
            "min_age": 25,
            "max_age": 40,
            "gender": "Male",
            "min_income": 50000,
            "max_income": 100000,
            "KYC_status": "Y",
            "Credit_score": 700,
            "Social_Media_Active": "Y",
        }
        body = _build_filter_body(group, app_installed="Y", existing_customer="Y")

        assert body["min_age"] == 25
        assert body["max_age"] == 40
        assert body["gender"] == ["Male"]
        assert body["min_monthly_income"] == 50000
        assert body["max_monthly_income"] == 100000
        assert body["kyc_status"] == "Y"
        assert body["min_credit_score"] == 700
        assert body["social_media_active"] == "Y"
        assert body["app_installed"] == "Y"
        assert body["existing_customer"] == "Y"

    def test_build_filter_body_omits_none_fields(self):
        from app.agents.segmentation import _build_filter_body

        body = _build_filter_body({}, app_installed=None, existing_customer="N")

        assert "min_age" not in body
        assert "max_age" not in body
        assert "app_installed" not in body
        assert body["existing_customer"] == "N"
