"""Mock Campaign API client with retry logic and cold-start handling.

Base URL: https://mock-campaign-api.onrender.com

The API may take 30-50 seconds on first request after 15 minutes idle
(Render.com cold start). All calls use a 60-second timeout with
exponential backoff (3 retries: 5s → 10s → 20s).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASE_URL = "https://mock-campaign-api.onrender.com"
DEFAULT_TIMEOUT = 60  # seconds — accommodates cold starts
MAX_RETRIES = 3


def _build_session() -> requests.Session:
    session = requests.Session()
    retry_cfg = Retry(
        total=0,  # Manual retry logic below; urllib3 retries are disabled
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_cfg)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class MockCampaignAPIError(Exception):
    """Raised when the Mock Campaign API returns an unexpected error."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Mock API error {status_code}: {detail}")


class MockCampaignClient:
    """Synchronous HTTP client for the Mock Campaign API.

    Handles cold starts, timeouts, and transient errors via exponential
    backoff retries.  Each public method wraps its request in
    ``_request_with_retry`` which performs up to ``MAX_RETRIES`` attempts.
    """

    def __init__(self, base_url: str = BASE_URL, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = _build_session()

    # ── Internal helpers ───────────────────────────────────────────────────

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        max_retries: int = MAX_RETRIES,
    ) -> Any:
        """Execute an HTTP request with retry/backoff for cold-start tolerance.

        Retry schedule: 5s → 10s → 20s (exponential, base 5).

        Raises:
            MockCampaignAPIError: For 4xx errors that should not be retried (e.g. 400, 404).
            requests.exceptions.Timeout: After all retries exhausted on timeout.
            requests.exceptions.RequestException: For other network-level failures.
        """
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                t0 = time.monotonic()
                response = self._session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    timeout=self.timeout,
                )
                elapsed = time.monotonic() - t0
                if elapsed > 10:
                    logger.warning(
                        "Mock API cold-start detected",
                        extra={"path": path, "elapsed_seconds": round(elapsed, 2)},
                    )

                logger.debug(
                    "Mock API response",
                    extra={
                        "method": method,
                        "path": path,
                        "status": response.status_code,
                        "elapsed": round(elapsed, 2),
                        "attempt": attempt,
                    },
                )

                # 400/404 are client errors – don't retry
                if response.status_code == 400:
                    detail = _extract_detail(response)
                    raise MockCampaignAPIError(400, detail)
                if response.status_code == 404:
                    detail = _extract_detail(response)
                    raise MockCampaignAPIError(404, detail)

                response.raise_for_status()
                return response.json()

            except MockCampaignAPIError:
                raise
            except requests.exceptions.Timeout as exc:
                last_exc = exc
                logger.warning(
                    "Mock API timeout",
                    extra={"path": path, "attempt": attempt, "timeout": self.timeout},
                )
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "Mock API network error",
                    extra={"path": path, "attempt": attempt, "error": str(exc)},
                )

            if attempt < max_retries:
                wait = 5 * (2 ** (attempt - 1))  # 5s, 10s, 20s
                logger.info("Mock API retry in %ds (attempt %d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)

        raise last_exc  # type: ignore[misc]

    # ── Public API ─────────────────────────────────────────────────────────

    def get_customers(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Fetch a paginated batch of customers.

        Args:
            limit:  Maximum number of records to return (default 100).
            offset: Zero-based starting position.

        Returns:
            List of customer dicts with 18 demographic fields.
        """
        result = self._request_with_retry(
            "GET",
            "/api/customers",
            params={"limit": limit, "offset": offset},
        )
        if isinstance(result, list):
            return result
        # Some API versions wrap in {"customers": [...]}
        return result.get("customers", result.get("data", []))

    def get_customer_count(self) -> int:
        """Return total number of customers available in the Mock API."""
        result = self._request_with_retry("GET", "/api/customers/count")
        if isinstance(result, dict):
            return int(result.get("count", result.get("total", 0)))
        return int(result)

    def validate_customer_ids(self, customer_ids: list[str]) -> dict[str, Any]:
        """Validate a list of customer IDs against the Mock API.

        Args:
            customer_ids: List of CUST#### format IDs.

        Returns:
            Dict with ``valid_ids``, ``invalid_ids``, and ``total_valid`` keys.
        """
        if not customer_ids:
            raise MockCampaignAPIError(400, "customer_ids list must not be empty")
        return self._request_with_retry(
            "POST",
            "/api/customers/validate",
            json={"customer_ids": customer_ids},
        )

    def schedule_campaign(
        self,
        customer_ids: list[str],
        subject: str,
        body: str,
        scheduled_time: str | datetime,
        segment_name: str,
        variant_id: str,
        campaign_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Schedule an email campaign via the Mock API.

        Args:
            customer_ids:      Validated CUST#### IDs to target.
            subject:           Email subject (40-60 chars for best scoring).
            body:              HTML email body (100-200 words for best scoring).
            scheduled_time:    ISO-8601 datetime or datetime object.
            segment_name:      Logical segment label.
            variant_id:        Internal variant identifier.
            campaign_metadata: Optional metadata dict forwarded as-is.

        Returns:
            Dict with ``campaign_id`` (Mock API UUID), ``status``, and
            ``total_customers``.
        """
        if isinstance(scheduled_time, datetime):
            scheduled_time = scheduled_time.isoformat()

        payload: dict[str, Any] = {
            "customer_ids": customer_ids,
            "subject": subject,
            "body": body,
            "scheduled_time": scheduled_time,
            "segment_name": segment_name,
            "variant_id": variant_id,
        }
        if campaign_metadata:
            payload["campaign_metadata"] = campaign_metadata

        logger.info(
            "Scheduling Mock API campaign",
            extra={
                "variant_id": variant_id,
                "segment_name": segment_name,
                "customer_count": len(customer_ids),
                "scheduled_time": scheduled_time,
            },
        )
        return self._request_with_retry("POST", "/api/campaigns/schedule", json=payload)

    def get_campaign_metrics(self, campaign_id: str) -> dict[str, Any]:
        """Fetch aggregated performance metrics for a Mock API campaign.

        Args:
            campaign_id: UUID returned by ``schedule_campaign``.

        Returns:
            Dict with ``open_rate``, ``click_rate``, ``click_through_rate``,
            ``total_sent``, ``unique_opens``, ``unique_clicks`` (rates as 0.0–1.0).
        """
        return self._request_with_retry("GET", f"/api/campaigns/{campaign_id}/metrics")

    def get_campaign_results(
        self, campaign_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch per-customer open/click outcomes for a Mock API campaign.

        Args:
            campaign_id: UUID returned by ``schedule_campaign``.
            limit:       Maximum number of results to fetch.

        Returns:
            List of dicts with ``customer_id``, ``opened``, ``clicked``,
            ``open_probability``, and ``click_probability``.
        """
        result = self._request_with_retry(
            "GET",
            f"/api/campaigns/{campaign_id}/results",
            params={"limit": limit},
        )
        if isinstance(result, list):
            return result
        return result.get("results", result.get("data", []))

    def filter_customers(self, criteria: dict[str, Any]) -> dict[str, Any]:
        """Filter the customer cohort by criteria and return matching IDs.

        Args:
            criteria: Filter body matching the /api/customers/filter schema.
                      All fields optional; omit to skip that filter.

        Returns:
            Dict with ``count`` (int) and ``customer_ids`` (list[str]).
        """
        return self._request_with_retry(
            "POST",
            "/api/customers/filter",
            json=criteria,
        )

    def health_check(self) -> dict[str, Any]:
        """Ping the Mock API root endpoint and return connectivity status.

        Returns:
            Dict with ``status`` ("ok" or "error"), ``latency_ms``, and
            optionally ``detail`` on failure.
        """
        t0 = time.monotonic()
        try:
            self._request_with_retry("GET", "/", max_retries=1)
            latency_ms = round((time.monotonic() - t0) * 1000, 2)
            logger.info("Mock API health check OK (%.0fms)", latency_ms)
            return {"status": "ok", "latency_ms": latency_ms}
        except Exception as exc:
            latency_ms = round((time.monotonic() - t0) * 1000, 2)
            logger.warning("Mock API health check failed: %s", exc)
            return {"status": "error", "latency_ms": latency_ms, "detail": str(exc)[:200]}

    # ── Private validation helpers ─────────────────────────────────────────

    def _log_api_call(
        self,
        operation: str,
        params: dict[str, Any],
        success: bool,
        elapsed_ms: float,
        error: str | None = None,
    ) -> None:
        """Emit a structured log entry for an API call."""
        entry: dict[str, Any] = {
            "operation": operation,
            "success": success,
            "elapsed_ms": elapsed_ms,
            **params,
        }
        if error:
            entry["error"] = error
        if success:
            logger.info("Mock API call succeeded", extra=entry)
        else:
            logger.error("Mock API call failed", extra=entry)

    @staticmethod
    def _validate_campaign_response(response: dict[str, Any]) -> None:
        """Raise ``ValueError`` if the schedule_campaign response is malformed."""
        required = {"campaign_id", "status"}
        missing = required - response.keys()
        if missing:
            raise ValueError(f"schedule_campaign response missing fields: {missing}")
        if not response.get("campaign_id"):
            raise ValueError("schedule_campaign returned empty campaign_id")

    @staticmethod
    def _validate_metrics_response(response: dict[str, Any]) -> None:
        """Raise ``ValueError`` if the get_campaign_metrics response is malformed."""
        rate_fields = {"open_rate", "click_rate", "click_through_rate"}
        missing = rate_fields - response.keys()
        if missing:
            raise ValueError(f"metrics response missing fields: {missing}")
        for field in rate_fields:
            val = response.get(field)
            if val is not None and not (0.0 <= float(val) <= 1.0):
                raise ValueError(f"metrics field '{field}' out of range [0, 1]: {val}")

    @staticmethod
    def _validate_customer_data(customer: dict[str, Any]) -> None:
        """Raise ``ValueError`` if a customer record is missing required fields."""
        required = {"customer_id"}
        missing = required - customer.keys()
        if missing:
            raise ValueError(f"customer record missing fields: {missing}")
        cid = customer.get("customer_id", "")
        if not str(cid).startswith("CUST"):
            raise ValueError(f"customer_id does not match CUST#### format: {cid!r}")


def _extract_detail(response: requests.Response) -> str:
    """Pull a human-readable error message from an API error response."""
    try:
        data = response.json()
        return str(data.get("detail", data.get("message", data.get("error", response.text))))
    except Exception:
        return response.text[:200]
