"""Error scenario tests for Mock Campaign API interactions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from app.external.mock_campaign_client import MockCampaignAPIError, MockCampaignClient


def _make_client() -> MockCampaignClient:
    return MockCampaignClient(base_url="https://mock-test.example.com", timeout=5)


@pytest.mark.unit
class TestMockAPIErrors:

    # ── Cold start / timeout ──────────────────────────────────────

    def test_timeout_raises_after_retries(self):
        client = _make_client()
        with patch.object(client._session, "request", side_effect=requests.exceptions.Timeout("cold start")):
            with pytest.raises(requests.exceptions.Timeout):
                client.get_customers()

    def test_connection_error_raises(self):
        client = _make_client()
        with patch.object(
            client._session, "request", side_effect=requests.exceptions.ConnectionError("refused")
        ):
            with pytest.raises(requests.exceptions.ConnectionError):
                client.get_customer_count()

    # ── 400 validation errors (no retry expected) ─────────────────

    def test_400_on_invalid_customer_ids_raises(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"detail": "Invalid customer IDs: ['FAKE_ID']"}
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)

        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises((MockCampaignAPIError, requests.exceptions.HTTPError)):
                client.validate_customer_ids(["FAKE_ID"])

    def test_400_on_schedule_invalid_payload_raises(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"detail": "Bad request: empty customer list"}
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)

        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises((MockCampaignAPIError, requests.exceptions.HTTPError)):
                client.schedule_campaign(
                    customer_ids=[],
                    subject="Test",
                    body="Test",
                    scheduled_time="2026-01-01T09:00:00Z",
                    segment_name="test",
                    variant_id="var-1",
                )

    # ── 404 not found ─────────────────────────────────────────────

    def test_404_on_unknown_campaign_metrics_raises(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "Campaign not found"}
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)

        with patch.object(client._session, "request", return_value=mock_resp):
            with pytest.raises((MockCampaignAPIError, requests.exceptions.HTTPError)):
                client.get_campaign_metrics("nonexistent-campaign-id")

    # ── 500 server errors ─────────────────────────────────────────

    def test_500_on_health_check_is_caught(self):
        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.side_effect = Exception("not JSON")
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)

        with patch.object(client._session, "request", return_value=mock_resp):
            result = client.health_check()
            assert result["status"] == "error"

    # ── MockCampaignAPIError ──────────────────────────────────────

    def test_mock_campaign_api_error_attributes(self):
        err = MockCampaignAPIError(status_code=422, detail="Unprocessable entity")
        assert err.status_code == 422
        assert "Unprocessable" in err.detail

    def test_mock_campaign_api_error_is_exception(self):
        err = MockCampaignAPIError(400, "bad input")
        assert isinstance(err, Exception)

    # ── Retry behaviour ───────────────────────────────────────────

    def test_successful_retry_after_timeout(self):
        client = _make_client()
        good_resp = MagicMock()
        good_resp.status_code = 200
        # get_customer_count() checks "count" or "total" keys (not "total_customers")
        good_resp.json.return_value = {"count": 5000, "total": 5000}
        good_resp.raise_for_status.return_value = None

        call_count = [0]

        def _side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise requests.exceptions.Timeout("cold start")
            return good_resp

        with patch.object(client._session, "request", side_effect=_side_effect):
            result = client.get_customer_count()
            assert result == 5000
            assert call_count[0] == 2
