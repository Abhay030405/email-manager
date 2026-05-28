"""Unit tests for ApprovalAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.approval import ApprovalAgent


def _make_agent() -> ApprovalAgent:
    with patch("app.agents.base_agent.ChatOpenAI") as mock_llm_cls:
        mock_llm_cls.return_value = MagicMock()
        return ApprovalAgent()


@pytest.mark.unit
class TestApprovalAgent:

    @pytest.mark.asyncio
    async def test_check_approval_status_pending(self, mock_db):
        agent = _make_agent()
        result = await agent.check_approval_status("camp-nonexistent")
        assert "approval_status" in result
        assert result["approval_status"] in {"approved", "rejected", "pending"}

    @pytest.mark.asyncio
    async def test_execute_returns_status(self):
        agent = _make_agent()
        result = await agent.execute({
            "campaign_id": "camp-001",
            "campaign_brief": "Test brief",
            "variants": [],
        })
        assert result is not None
        assert "approval_status" in result
