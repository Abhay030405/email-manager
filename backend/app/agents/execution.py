"""Campaign Execution Agent — schedules email campaigns via the Mock Campaign API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import BaseAgent
from app.db.mongodb import MongoDB
from app.db.repositories.variant_repo import VariantRepository
from app.external.mock_campaign_client import MockCampaignClient, MockCampaignAPIError
from app.models.variant import VariantStatus

logger = logging.getLogger(__name__)


class ExecutionAgent(BaseAgent):
    """Executes approved campaign variants by scheduling them via the Mock Campaign API.

    For each variant:
    1. Validates customer IDs with the Mock API.
    2. Schedules via POST /api/campaigns/schedule.
    3. Stores the returned mock_campaign_id in MongoDB.
    4. Returns a mapping of variant_id → mock_campaign_id.
    """

    def __init__(self) -> None:
        super().__init__(model_name="gpt-4", temperature=0.0, max_tokens=512)
        self._client = MockCampaignClient()

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Delegate to execute_campaign using input_data fields."""
        campaign_id = input_data.get("campaign_id", "")
        variants = input_data.get("variants", [])
        return await self.execute_campaign(campaign_id, variants)

    async def execute_campaign(
        self, campaign_id: str, approved_variants: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Schedule all approved variants via the Mock Campaign API.

        Args:
            campaign_id:       Internal campaign identifier.
            approved_variants: List of variant dicts from campaign state.

        Returns:
            Dict with ``execution_status``, ``mock_api_campaign_ids``
            (variant_id → Mock API campaign_id), and ``metrics``.
        """
        self._log_action("execute_campaign", {
            "campaign_id": campaign_id,
            "variant_count": len(approved_variants),
        })

        mock_api_campaign_ids: dict[str, str] = {}
        errors: list[str] = []
        repo = VariantRepository(MongoDB.get_db())

        for variant in approved_variants:
            variant_id = variant.get("variant_id", "")
            segment_name = variant.get("segment_name", "")
            customer_ids: list[str] = variant.get("customer_ids", [])
            subject = variant.get("subject_line", variant.get("subject", ""))
            body = variant.get("email_body", variant.get("body", ""))
            send_time = variant.get("send_time")

            if not customer_ids:
                logger.warning("No customer_ids for variant %s — skipping", variant_id)
                errors.append(f"No customer_ids for variant {variant_id}")
                continue

            # Validate customer IDs with Mock API
            try:
                validation = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda cids=customer_ids: self._client.validate_customer_ids(cids),
                )
                valid_ids: list[str] = validation.get("valid_ids", customer_ids)
                if not valid_ids:
                    errors.append(f"All customer IDs invalid for variant {variant_id}")
                    continue
            except MockCampaignAPIError as exc:
                logger.error("Customer validation failed for %s: %s", variant_id, exc)
                valid_ids = customer_ids
                errors.append(f"Validation error for {variant_id}: {exc.detail}")

            # Normalise send_time to ISO string
            if isinstance(send_time, datetime):
                scheduled_time = send_time.isoformat()
            elif isinstance(send_time, str):
                scheduled_time = send_time
            else:
                scheduled_time = datetime.now(tz=timezone.utc).isoformat()

            # Schedule campaign via Mock API
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda vid=variant_id, s=subject, b=body, st=scheduled_time, sn=segment_name, vids=valid_ids: (
                        self._client.schedule_campaign(
                            customer_ids=vids,
                            subject=s,
                            body=b,
                            scheduled_time=st,
                            segment_name=sn,
                            variant_id=vid,
                            campaign_metadata={"internal_campaign_id": campaign_id},
                        )
                    ),
                )
                mock_campaign_id: str = response.get("campaign_id", "")
                mock_api_campaign_ids[variant_id] = mock_campaign_id
                logger.info(
                    "Scheduled Mock API campaign",
                    extra={
                        "variant_id": variant_id,
                        "mock_campaign_id": mock_campaign_id,
                        "customers": len(valid_ids),
                    },
                )
                # Persist mock_campaign_id to MongoDB
                try:
                    await repo.update_mock_campaign_id(variant_id, mock_campaign_id)
                except Exception as db_exc:
                    logger.warning("Failed to persist mock_campaign_id: %s", db_exc)

            except MockCampaignAPIError as exc:
                logger.error("Mock API scheduling failed for %s: %s", variant_id, exc)
                errors.append(f"Scheduling error for {variant_id}: {exc.detail}")
            except Exception as exc:
                logger.error("Unexpected scheduling error for %s: %s", variant_id, exc)
                errors.append(f"Unexpected error for {variant_id}: {exc}")

        execution_status = "completed" if mock_api_campaign_ids else "failed"

        return {
            "execution_status": execution_status,
            "mock_api_campaign_ids": mock_api_campaign_ids,
            "metrics": {
                "emails_scheduled": len(mock_api_campaign_ids),
                "executed_at": datetime.now(tz=timezone.utc).isoformat(),
                "errors": errors,
            },
        }
