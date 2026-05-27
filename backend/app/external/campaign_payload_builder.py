"""Campaign payload builder — constructs and scores Mock API schedule payloads."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Optimal ranges per Mock API scoring criteria
_SUBJECT_MIN = 40
_SUBJECT_MAX = 60
_BODY_WORD_MIN = 100
_BODY_WORD_MAX = 200


class PayloadValidationError(ValueError):
    """Raised when a payload field fails validation."""


class CampaignPayloadBuilder:
    """Builds and validates payloads for the Mock Campaign API's schedule endpoint.

    Scoring guide (reflected in ``compute_optimization_score``):
    - Subject length 40-60 chars  → +0.4
    - Body word count 100-200     → +0.4
    - Scheduled ≥ 24 h in future  → +0.2
    Total possible: 1.0
    """

    def __init__(self, scheduled_offset_hours: int = 24) -> None:
        self._scheduled_offset_hours = scheduled_offset_hours

    # ── Public API ─────────────────────────────────────────────────────────

    def build_schedule_payload(
        self,
        customer_ids: list[str],
        subject: str,
        body: str,
        segment_name: str,
        variant_id: str,
        scheduled_time: str | datetime | None = None,
        campaign_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a validated payload dict ready for ``MockCampaignClient.schedule_campaign``.

        Raises:
            PayloadValidationError: If any field fails validation.
        """
        if not customer_ids:
            raise PayloadValidationError("customer_ids must not be empty")

        validated_subject = self._validate_subject(subject)
        validated_body = self._validate_body(body)
        resolved_time = self._resolve_scheduled_time(scheduled_time)
        score = self.compute_optimization_score(validated_subject, validated_body, resolved_time)

        logger.info(
            "Built campaign payload",
            extra={
                "variant_id": variant_id,
                "segment_name": segment_name,
                "customer_count": len(customer_ids),
                "subject_len": len(validated_subject),
                "body_words": _word_count(validated_body),
                "optimization_score": round(score, 3),
            },
        )

        payload: dict[str, Any] = {
            "customer_ids": customer_ids,
            "subject": validated_subject,
            "body": validated_body,
            "scheduled_time": resolved_time,
            "segment_name": segment_name,
            "variant_id": variant_id,
        }
        if campaign_metadata:
            payload["campaign_metadata"] = campaign_metadata
        return payload

    def compute_optimization_score(
        self,
        subject: str,
        body: str,
        scheduled_time: str | None = None,
    ) -> float:
        """Return a 0.0–1.0 score estimating Mock API scoring performance.

        Higher scores correlate with better open/click rates in the Mock API.
        """
        score = 0.0

        subject_len = len(subject.strip())
        if _SUBJECT_MIN <= subject_len <= _SUBJECT_MAX:
            score += 0.4
        elif subject_len > 0:
            # Partial credit: 0.2 if within 10 chars of optimal range
            if _SUBJECT_MIN - 10 <= subject_len <= _SUBJECT_MAX + 10:
                score += 0.2

        word_count = _word_count(body)
        if _BODY_WORD_MIN <= word_count <= _BODY_WORD_MAX:
            score += 0.4
        elif word_count > 0:
            if _BODY_WORD_MIN - 20 <= word_count <= _BODY_WORD_MAX + 30:
                score += 0.2

        if scheduled_time:
            try:
                dt = _parse_dt(scheduled_time)
                hours_ahead = (dt - datetime.now(tz=timezone.utc)).total_seconds() / 3600
                if hours_ahead >= 24:
                    score += 0.2
                elif hours_ahead >= 1:
                    score += 0.1
            except Exception:
                pass

        return round(min(score, 1.0), 4)

    # ── Private helpers ────────────────────────────────────────────────────

    def _validate_subject(self, subject: str) -> str:
        subject = subject.strip()
        if not subject:
            raise PayloadValidationError("subject must not be empty")
        if len(subject) < 5:
            raise PayloadValidationError(f"subject too short ({len(subject)} chars); minimum 5")
        if len(subject) > 200:
            raise PayloadValidationError(f"subject too long ({len(subject)} chars); maximum 200")
        if len(subject) < _SUBJECT_MIN or len(subject) > _SUBJECT_MAX:
            logger.warning(
                "Subject length %d is outside optimal range %d-%d",
                len(subject),
                _SUBJECT_MIN,
                _SUBJECT_MAX,
            )
        return subject

    def _validate_body(self, body: str) -> str:
        body = body.strip()
        if not body:
            raise PayloadValidationError("body must not be empty")
        words = _word_count(body)
        if words < 10:
            raise PayloadValidationError(f"body too short ({words} words); minimum 10")
        if words < _BODY_WORD_MIN or words > _BODY_WORD_MAX:
            logger.warning(
                "Body word count %d is outside optimal range %d-%d",
                words,
                _BODY_WORD_MIN,
                _BODY_WORD_MAX,
            )
        return body

    def _resolve_scheduled_time(self, scheduled_time: str | datetime | None) -> str:
        if scheduled_time is None:
            dt = datetime.now(tz=timezone.utc) + timedelta(hours=self._scheduled_offset_hours)
            return dt.isoformat()
        if isinstance(scheduled_time, datetime):
            return scheduled_time.isoformat()
        # Validate the string is parseable
        try:
            _parse_dt(scheduled_time)
        except Exception as exc:
            raise PayloadValidationError(f"invalid scheduled_time: {exc}") from exc
        return scheduled_time


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _parse_dt(value: str) -> datetime:
    """Parse an ISO-8601 string to an aware datetime (UTC if no tz info)."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
