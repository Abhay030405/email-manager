"""Approval Coordinator Agent — checks campaign approval status from MongoDB."""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base_agent import BaseAgent
from app.db.mongodb import MongoDB
from app.db.repositories.campaign_repo import CampaignRepository
from app.models.campaign import CampaignStatus

logger = logging.getLogger(__name__)


class ApprovalAgent(BaseAgent):
    """Checks whether a campaign has been approved, rejected, or is still pending.

    Reads approval state from MongoDB rather than calling an LLM, since this
    decision is driven by human reviewers interacting with the CampaignX UI.
    """

    def __init__(self) -> None:
        super().__init__(model_name="gpt-4", temperature=0.0, max_tokens=256)

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Delegate to check_approval_status using campaign_id from input_data."""
        campaign_id = input_data.get("campaign_id", "")
        return await self.check_approval_status(campaign_id)

    async def check_approval_status(self, campaign_id: str) -> dict[str, Any]:
        """Return current approval status for the given campaign.

        Args:
            campaign_id: The internal campaign identifier.

        Returns:
            Dict with ``approval_status`` key: ``"approved"``, ``"rejected"``, or ``"pending"``.
        """
        self._log_action("check_approval_status", {"campaign_id": campaign_id})

        db = MongoDB.get_db()
        repo = CampaignRepository(db)
        campaign = await repo.find_by_id(campaign_id)

        if campaign is None:
            logger.warning("Campaign not found for approval check: %s", campaign_id)
            return {"approval_status": "pending"}

        status_map = {
            CampaignStatus.APPROVED: "approved",
            CampaignStatus.REJECTED: "rejected",
            CampaignStatus.PENDING_APPROVAL: "pending",
        }
        approval_status = status_map.get(campaign.status, "pending")
        self._log_action("approval_status_resolved", {
            "campaign_id": campaign_id,
            "campaign_status": campaign.status,
            "approval_status": approval_status,
        })
        return {"approval_status": approval_status}
