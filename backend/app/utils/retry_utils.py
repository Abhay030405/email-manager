"""Retry utilities with exponential backoff for Mock Campaign API calls."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.external.mock_campaign_client import MockCampaignAPIError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# 4xx codes that should never be retried
_NO_RETRY_CODES = {400, 401, 403, 404, 422}


def retry_with_exponential_backoff(
    func: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 5.0,
    max_delay: float = 60.0,
    operation_name: str = "operation",
) -> T:
    """Call *func* synchronously, retrying on transient errors with exponential backoff.

    Args:
        func:            Zero-argument callable to invoke.
        max_retries:     Maximum number of total attempts (default 3).
        base_delay:      Initial wait in seconds (doubles each attempt).
        max_delay:       Cap on individual wait period.
        operation_name:  Label used in log messages.

    Returns:
        The return value of *func* on the first successful call.

    Raises:
        MockCampaignAPIError: Immediately for 4xx client errors (not retried).
        Exception:            After all retries are exhausted.
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            result = func()
            if attempt > 1:
                logger.info("%s succeeded on attempt %d/%d", operation_name, attempt, max_retries)
            return result
        except MockCampaignAPIError as exc:
            if exc.status_code in _NO_RETRY_CODES:
                logger.error("%s failed with non-retryable %d: %s", operation_name, exc.status_code, exc.detail)
                raise
            last_exc = exc
            logger.warning("%s API error %d on attempt %d/%d: %s", operation_name, exc.status_code, attempt, max_retries, exc.detail)
        except Exception as exc:
            last_exc = exc
            logger.warning("%s failed on attempt %d/%d: %s", operation_name, attempt, max_retries, exc)

        if attempt < max_retries:
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.info("%s retrying in %.1fs (attempt %d/%d)", operation_name, delay, attempt + 1, max_retries)
            time.sleep(delay)

    raise last_exc  # type: ignore[misc]


async def call_mock_api_with_retry(
    func: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 5.0,
    max_delay: float = 60.0,
    operation_name: str = "mock_api_call",
) -> T:
    """Async wrapper: runs *func* in a thread executor with exponential backoff.

    Use this from async agents so the sync requests library doesn't block
    the event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: retry_with_exponential_backoff(
            func,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            operation_name=operation_name,
        ),
    )


async def retry_batch_operation(
    items: list[Any],
    operation: Callable[[Any], Any],
    *,
    max_retries: int = 3,
    base_delay: float = 2.0,
    operation_name: str = "batch_operation",
) -> dict[str, Any]:
    """Apply *operation* to each item in *items*, retrying failures independently.

    Args:
        items:          List of items to process.
        operation:      Async callable that accepts a single item.
        max_retries:    Retry limit per item.
        base_delay:     Initial backoff in seconds.
        operation_name: Label for logging.

    Returns:
        Dict with ``results`` (list), ``errors`` (dict item→error), and
        ``success_count`` / ``error_count`` summary fields.
    """
    results: list[Any] = []
    errors: dict[str, str] = {}

    for item in items:
        key = str(item)
        last_exc: Exception | None = None
        succeeded = False

        for attempt in range(1, max_retries + 1):
            try:
                result = await operation(item)
                results.append(result)
                succeeded = True
                break
            except MockCampaignAPIError as exc:
                if exc.status_code in _NO_RETRY_CODES:
                    errors[key] = f"non-retryable {exc.status_code}: {exc.detail}"
                    break
                last_exc = exc
            except Exception as exc:
                last_exc = exc

            if attempt < max_retries:
                delay = min(base_delay * (2 ** (attempt - 1)), 30.0)
                logger.warning("%s item %s attempt %d/%d failed — retrying in %.1fs", operation_name, key, attempt, max_retries, delay)
                await asyncio.sleep(delay)

        if not succeeded and key not in errors:
            errors[key] = str(last_exc) if last_exc else "unknown error"

    return {
        "results": results,
        "errors": errors,
        "success_count": len(results),
        "error_count": len(errors),
    }
