"""Unit tests for retry_utils module."""

import pytest

from app.external.mock_campaign_client import MockCampaignAPIError
from app.utils.retry_utils import retry_with_exponential_backoff, call_mock_api_with_retry


@pytest.mark.unit
class TestRetryWithExponentialBackoff:

    def test_succeeds_on_first_attempt(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = retry_with_exponential_backoff(func, max_retries=3, base_delay=0)
        assert result == "success"
        assert call_count == 1

    def test_retries_on_generic_exception(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "ok"

        result = retry_with_exponential_backoff(func, max_retries=3, base_delay=0)
        assert result == "ok"
        assert call_count == 3

    def test_raises_after_max_retries_exhausted(self):
        def always_fail():
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError, match="always fails"):
            retry_with_exponential_backoff(always_fail, max_retries=2, base_delay=0)

    def test_no_retry_on_400_mock_api_error(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            raise MockCampaignAPIError(400, "Bad request")

        with pytest.raises(MockCampaignAPIError) as exc_info:
            retry_with_exponential_backoff(func, max_retries=3, base_delay=0)

        assert exc_info.value.status_code == 400
        assert call_count == 1

    def test_no_retry_on_404_mock_api_error(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            raise MockCampaignAPIError(404, "Not found")

        with pytest.raises(MockCampaignAPIError):
            retry_with_exponential_backoff(func, max_retries=3, base_delay=0)

        assert call_count == 1

    def test_retries_on_502_mock_api_error(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MockCampaignAPIError(502, "Bad gateway")
            return {"data": "ok"}

        result = retry_with_exponential_backoff(func, max_retries=3, base_delay=0)
        assert result == {"data": "ok"}
        assert call_count == 3

    def test_no_retry_on_403_mock_api_error(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            raise MockCampaignAPIError(403, "Forbidden")

        with pytest.raises(MockCampaignAPIError):
            retry_with_exponential_backoff(func, max_retries=3, base_delay=0)

        assert call_count == 1

    def test_max_retries_one_immediate_result(self):
        def func():
            return 42

        result = retry_with_exponential_backoff(func, max_retries=1, base_delay=0)
        assert result == 42


@pytest.mark.unit
class TestCallMockApiWithRetry:

    @pytest.mark.asyncio
    async def test_async_wrapper_succeeds(self):
        def sync_func():
            return {"result": "ok"}

        result = await call_mock_api_with_retry(sync_func, max_retries=1, base_delay=0)
        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_async_wrapper_propagates_non_retryable_error(self):
        def sync_func():
            raise MockCampaignAPIError(400, "Bad request")

        with pytest.raises(MockCampaignAPIError) as exc_info:
            await call_mock_api_with_retry(sync_func, max_retries=3, base_delay=0)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_async_wrapper_retries_transient(self):
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise MockCampaignAPIError(503, "Service unavailable")
            return "recovered"

        result = await call_mock_api_with_retry(func, max_retries=3, base_delay=0)
        assert result == "recovered"
        assert call_count == 2
