"""Tests for retry_utils — no real HTTP calls."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, call

import pytest

from app.external.mock_campaign_client import MockCampaignAPIError
from app.utils.retry_utils import (
    call_mock_api_with_retry,
    retry_batch_operation,
    retry_with_exponential_backoff,
)


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── retry_with_exponential_backoff ────────────────────────────────────────────

def test_success_on_first_attempt():
    func = MagicMock(return_value="ok")
    result = retry_with_exponential_backoff(func, max_retries=3, base_delay=0.0)
    assert result == "ok"
    assert func.call_count == 1


def test_retries_on_transient_error_then_succeeds():
    func = MagicMock(side_effect=[RuntimeError("transient"), RuntimeError("transient"), "ok"])
    result = retry_with_exponential_backoff(func, max_retries=3, base_delay=0.0)
    assert result == "ok"
    assert func.call_count == 3


def test_raises_after_all_retries_exhausted():
    func = MagicMock(side_effect=RuntimeError("always fails"))
    with pytest.raises(RuntimeError):
        retry_with_exponential_backoff(func, max_retries=3, base_delay=0.0)
    assert func.call_count == 3


def test_non_retryable_400_raises_immediately():
    func = MagicMock(side_effect=MockCampaignAPIError(400, "bad request"))
    with pytest.raises(MockCampaignAPIError):
        retry_with_exponential_backoff(func, max_retries=3, base_delay=0.0)
    assert func.call_count == 1


def test_non_retryable_404_raises_immediately():
    func = MagicMock(side_effect=MockCampaignAPIError(404, "not found"))
    with pytest.raises(MockCampaignAPIError):
        retry_with_exponential_backoff(func, max_retries=3, base_delay=0.0)
    assert func.call_count == 1


def test_retryable_500_is_retried():
    func = MagicMock(side_effect=[MockCampaignAPIError(500, "server error"), "ok"])
    result = retry_with_exponential_backoff(func, max_retries=2, base_delay=0.0)
    assert result == "ok"


# ── call_mock_api_with_retry (async) ──────────────────────────────────────────

def test_call_mock_api_with_retry_async():
    func = MagicMock(return_value={"status": "ok"})
    result = run(call_mock_api_with_retry(func, max_retries=1, base_delay=0.0))
    assert result["status"] == "ok"


def test_call_mock_api_with_retry_propagates_non_retryable():
    func = MagicMock(side_effect=MockCampaignAPIError(400, "bad"))
    with pytest.raises(MockCampaignAPIError):
        run(call_mock_api_with_retry(func, max_retries=2, base_delay=0.0))


# ── retry_batch_operation ──────────────────────────────────────────────────────

def test_batch_all_succeed():
    async def op(item):
        return item * 2

    result = run(retry_batch_operation([1, 2, 3], op, base_delay=0.0))
    assert result["success_count"] == 3
    assert result["error_count"] == 0
    assert set(result["results"]) == {2, 4, 6}


def test_batch_partial_failure():
    async def op(item):
        if item == 2:
            raise RuntimeError("fail on 2")
        return item

    result = run(retry_batch_operation([1, 2, 3], op, max_retries=1, base_delay=0.0))
    assert result["success_count"] == 2
    assert result["error_count"] == 1
    assert "2" in result["errors"]


def test_batch_non_retryable_counted_once():
    async def op(item):
        raise MockCampaignAPIError(404, "not found")

    result = run(retry_batch_operation([1], op, max_retries=3, base_delay=0.0))
    assert result["error_count"] == 1
    # Should only attempt once (non-retryable 404)
    assert "non-retryable" in result["errors"]["1"]


def test_batch_empty_list():
    result = run(retry_batch_operation([], MagicMock(), base_delay=0.0))
    assert result["success_count"] == 0
    assert result["error_count"] == 0
