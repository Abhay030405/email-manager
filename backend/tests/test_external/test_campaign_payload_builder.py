"""Tests for CampaignPayloadBuilder."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.external.campaign_payload_builder import (
    CampaignPayloadBuilder,
    PayloadValidationError,
)

BUILDER = CampaignPayloadBuilder(scheduled_offset_hours=24)

# Valid 40-60 char subject
GOOD_SUBJECT = "Exclusive Diwali Deals for Premium Electronics!"  # 49 chars
# Valid 100-200 word body
GOOD_BODY = " ".join(["word"] * 120)


# ── build_schedule_payload ────────────────────────────────────────────────────

def test_build_payload_returns_dict_with_required_keys():
    payload = BUILDER.build_schedule_payload(
        customer_ids=["CUST0001"],
        subject=GOOD_SUBJECT,
        body=GOOD_BODY,
        segment_name="premium_segment",
        variant_id="variant_001",
    )
    assert "customer_ids" in payload
    assert "subject" in payload
    assert "body" in payload
    assert "scheduled_time" in payload
    assert "segment_name" in payload
    assert "variant_id" in payload


def test_build_payload_passes_metadata():
    payload = BUILDER.build_schedule_payload(
        customer_ids=["CUST0001"],
        subject=GOOD_SUBJECT,
        body=GOOD_BODY,
        segment_name="seg",
        variant_id="vid",
        campaign_metadata={"internal_id": "camp-123"},
    )
    assert payload["campaign_metadata"]["internal_id"] == "camp-123"


def test_build_payload_empty_customer_ids_raises():
    with pytest.raises(PayloadValidationError, match="customer_ids"):
        BUILDER.build_schedule_payload(
            customer_ids=[],
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            segment_name="seg",
            variant_id="vid",
        )


def test_build_payload_empty_subject_raises():
    with pytest.raises(PayloadValidationError):
        BUILDER.build_schedule_payload(
            customer_ids=["CUST0001"],
            subject="",
            body=GOOD_BODY,
            segment_name="seg",
            variant_id="vid",
        )


def test_build_payload_too_short_subject_raises():
    with pytest.raises(PayloadValidationError):
        BUILDER.build_schedule_payload(
            customer_ids=["CUST0001"],
            subject="Hi",
            body=GOOD_BODY,
            segment_name="seg",
            variant_id="vid",
        )


def test_build_payload_empty_body_raises():
    with pytest.raises(PayloadValidationError):
        BUILDER.build_schedule_payload(
            customer_ids=["CUST0001"],
            subject=GOOD_SUBJECT,
            body="",
            segment_name="seg",
            variant_id="vid",
        )


def test_build_payload_too_short_body_raises():
    with pytest.raises(PayloadValidationError, match="too short"):
        BUILDER.build_schedule_payload(
            customer_ids=["CUST0001"],
            subject=GOOD_SUBJECT,
            body="Short body",
            segment_name="seg",
            variant_id="vid",
        )


def test_build_payload_uses_provided_scheduled_time():
    t = "2026-06-01T10:00:00+00:00"
    payload = BUILDER.build_schedule_payload(
        customer_ids=["CUST0001"],
        subject=GOOD_SUBJECT,
        body=GOOD_BODY,
        segment_name="seg",
        variant_id="vid",
        scheduled_time=t,
    )
    assert payload["scheduled_time"] == t


def test_build_payload_invalid_scheduled_time_raises():
    with pytest.raises(PayloadValidationError, match="invalid scheduled_time"):
        BUILDER.build_schedule_payload(
            customer_ids=["CUST0001"],
            subject=GOOD_SUBJECT,
            body=GOOD_BODY,
            segment_name="seg",
            variant_id="vid",
            scheduled_time="not-a-date",
        )


def test_build_payload_defaults_scheduled_time_24h_ahead():
    before = datetime.now(tz=timezone.utc) + timedelta(hours=23)
    payload = BUILDER.build_schedule_payload(
        customer_ids=["CUST0001"],
        subject=GOOD_SUBJECT,
        body=GOOD_BODY,
        segment_name="seg",
        variant_id="vid",
    )
    scheduled = datetime.fromisoformat(payload["scheduled_time"])
    if scheduled.tzinfo is None:
        from datetime import timezone as tz2
        scheduled = scheduled.replace(tzinfo=tz2.utc)
    assert scheduled > before


# ── compute_optimization_score ────────────────────────────────────────────────

def test_score_perfect_subject_and_body():
    future = (datetime.now(tz=timezone.utc) + timedelta(hours=25)).isoformat()
    score = BUILDER.compute_optimization_score(GOOD_SUBJECT, GOOD_BODY, future)
    assert score == 1.0


def test_score_bad_subject_length():
    future = (datetime.now(tz=timezone.utc) + timedelta(hours=25)).isoformat()
    score = BUILDER.compute_optimization_score("Short", GOOD_BODY, future)
    assert score < 1.0


def test_score_zero_for_empty_subject_and_body():
    score = BUILDER.compute_optimization_score("", "")
    assert score == 0.0


def test_score_partial_credit_for_near_optimal():
    # 35-char subject: just outside 40-60 optimal but within ±10
    subject = "A" * 35
    score = BUILDER.compute_optimization_score(subject, GOOD_BODY)
    assert 0.0 < score < 1.0


def test_score_no_scheduled_time_skips_timing():
    score_no_time = BUILDER.compute_optimization_score(GOOD_SUBJECT, GOOD_BODY)
    score_with_time = BUILDER.compute_optimization_score(
        GOOD_SUBJECT, GOOD_BODY, (datetime.now(tz=timezone.utc) + timedelta(hours=25)).isoformat()
    )
    assert score_with_time > score_no_time


def test_score_capped_at_1():
    future = (datetime.now(tz=timezone.utc) + timedelta(hours=25)).isoformat()
    score = BUILDER.compute_optimization_score(GOOD_SUBJECT, GOOD_BODY, future)
    assert score <= 1.0
