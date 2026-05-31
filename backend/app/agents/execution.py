"""Campaign Execution Agent — schedules email campaigns via the Mock Campaign API."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import BaseAgent
from app.db.mongodb import MongoDB
from app.db.repositories.execution_log_repo import ExecutionLogRepository
from app.db.repositories.variant_repo import VariantRepository
from app.external.campaign_id_mapper import CampaignIDMapper
from app.external.campaign_payload_builder import CampaignPayloadBuilder, PayloadValidationError
from app.external.mock_campaign_client import MockCampaignClient, MockCampaignAPIError
from app.models.execution_log import ExecutionLog, ExecutionLogStatus
from app.models.variant import VariantStatus

logger = logging.getLogger(__name__)


class ExecutionAgent(BaseAgent):
    """Executes approved campaign variants by scheduling them via the Mock Campaign API.

    For each variant:
    1. Builds and validates the schedule payload.
    2. Validates customer IDs with the Mock API.
    3. Schedules via POST /api/campaigns/schedule.
    4. Stores the returned mock_campaign_id in MongoDB.
    5. Writes an ExecutionLog record for each attempt.
    6. Returns a CampaignIDMapper with all successful mappings.
    """

    def __init__(self) -> None:
        super().__init__(temperature=0.0, max_tokens=512)
        self._client = MockCampaignClient()
        self._payload_builder = CampaignPayloadBuilder()

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        campaign_id = input_data.get("campaign_id", "")
        variants = input_data.get("variants", [])
        return await self.execute_campaign(campaign_id, variants)

    async def execute_campaign(
        self, campaign_id: str, approved_variants: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Schedule all approved variants via the Mock Campaign API.

        Returns:
            Dict with ``execution_status``, ``mock_api_campaign_ids``
            (variant_id → Mock API campaign_id), and ``metrics``.
        """
        self._log_action("execute_campaign", {
            "campaign_id": campaign_id,
            "variant_count": len(approved_variants),
        })

        mapper = CampaignIDMapper()
        errors: list[str] = []
        db = MongoDB.get_db()
        variant_repo = VariantRepository(db)
        log_repo = ExecutionLogRepository(db)

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
                await _write_log(log_repo, campaign_id, variant_id, ExecutionLogStatus.SKIPPED,
                                 error="no customer_ids")
                continue

            # Build and validate payload
            try:
                self._payload_builder.build_schedule_payload(
                    customer_ids=customer_ids,
                    subject=subject,
                    body=body,
                    segment_name=segment_name,
                    variant_id=variant_id,
                    scheduled_time=send_time if isinstance(send_time, str) else None,
                )
            except PayloadValidationError as exc:
                logger.warning("Payload validation failed for %s: %s", variant_id, exc)
                errors.append(f"Payload error for {variant_id}: {exc}")
                await _write_log(log_repo, campaign_id, variant_id, ExecutionLogStatus.SKIPPED,
                                 error=str(exc))
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
                    await _write_log(log_repo, campaign_id, variant_id, ExecutionLogStatus.FAILED,
                                     customer_count=len(customer_ids),
                                     error="all customer IDs invalid")
                    continue
            except MockCampaignAPIError as exc:
                logger.error("Customer validation failed for %s: %s", variant_id, exc)
                valid_ids = customer_ids
                errors.append(f"Validation error for {variant_id}: {exc.detail}")

            # Normalise send_time
            if isinstance(send_time, datetime):
                scheduled_time = send_time.isoformat()
            elif isinstance(send_time, str):
                scheduled_time = send_time
            else:
                scheduled_time = datetime.now(tz=timezone.utc).isoformat()

            # Schedule via Mock API
            t0 = time.monotonic()
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
                elapsed_ms = round((time.monotonic() - t0) * 1000, 2)

                # Validate response
                self._client._validate_campaign_response(response)
                mock_campaign_id: str = response["campaign_id"]
                mapper.register(variant_id, mock_campaign_id)

                self._client._log_api_call(
                    "schedule_campaign",
                    {"variant_id": variant_id, "customer_count": len(valid_ids)},
                    success=True,
                    elapsed_ms=elapsed_ms,
                )
                logger.info(
                    "Scheduled Mock API campaign",
                    extra={"variant_id": variant_id, "mock_campaign_id": mock_campaign_id, "customers": len(valid_ids)},
                )

                try:
                    await variant_repo.update_mock_campaign_id(variant_id, mock_campaign_id)
                except Exception as db_exc:
                    logger.warning("Failed to persist mock_campaign_id: %s", db_exc)

                await _write_log(log_repo, campaign_id, variant_id, ExecutionLogStatus.SUCCESS,
                                 mock_campaign_id=mock_campaign_id,
                                 customer_count=len(valid_ids),
                                 elapsed_ms=elapsed_ms)

            except (MockCampaignAPIError, ValueError) as exc:
                elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
                error_msg = exc.detail if isinstance(exc, MockCampaignAPIError) else str(exc)
                logger.error("Mock API scheduling failed for %s: %s", variant_id, exc)
                errors.append(f"Scheduling error for {variant_id}: {error_msg}")
                self._client._log_api_call(
                    "schedule_campaign",
                    {"variant_id": variant_id},
                    success=False,
                    elapsed_ms=elapsed_ms,
                    error=error_msg,
                )
                await _write_log(log_repo, campaign_id, variant_id, ExecutionLogStatus.FAILED,
                                 elapsed_ms=elapsed_ms, error=error_msg)

            except Exception as exc:
                elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
                logger.error("Unexpected scheduling error for %s: %s", variant_id, exc)
                errors.append(f"Unexpected error for {variant_id}: {exc}")
                await _write_log(log_repo, campaign_id, variant_id, ExecutionLogStatus.FAILED,
                                 elapsed_ms=elapsed_ms, error=str(exc))

        execution_status = "completed" if len(mapper) > 0 else "failed"

        return {
            "execution_status": execution_status,
            "mock_api_campaign_ids": mapper.as_dict(),
            "metrics": {
                "emails_scheduled": len(mapper),
                "executed_at": datetime.now(tz=timezone.utc).isoformat(),
                "errors": errors,
            },
        }


async def _write_log(
    repo: ExecutionLogRepository,
    campaign_id: str,
    variant_id: str,
    status: ExecutionLogStatus,
    *,
    mock_campaign_id: str | None = None,
    customer_count: int = 0,
    elapsed_ms: float | None = None,
    error: str | None = None,
) -> None:
    try:
        log = ExecutionLog(
            campaign_id=campaign_id,
            variant_id=variant_id,
            mock_campaign_id=mock_campaign_id,
            status=status,
            customer_count=customer_count,
            elapsed_ms=elapsed_ms,
            error_message=error,
        )
        await repo.create(log)
    except Exception as exc:
        logger.warning("Failed to write execution log: %s", exc)
