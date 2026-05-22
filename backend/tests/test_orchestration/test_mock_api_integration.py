"""Tests for Mock Campaign API client and integration with orchestration graphs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.external.mock_campaign_client import (
    MockCampaignAPIError,
    MockCampaignClient,
)

# ── Mock response templates ─────────────────────────────────────────────────

MOCK_CUSTOMER_RESPONSE = [
    {
        "customer_id": "CUST0001",
        "Full_name": "Ravi Sharma",
        "email": "ravi.sharma@example.com",
        "Age": 30,
        "Gender": "Male",
        "Marital_Status": "Married",
        "Family_Size": 4,
        "Dependent count": 2,
        "Occupation": "Software Engineer",
        "Occupation type": "Full-time",
        "Monthly_Income": 85000,
        "KYC status": "Y",
        "City": "Mumbai",
        "Kids_in_Household": 1,
        "App_Installed": "Y",
        "Existing Customer": "Y",
        "Credit_score": 750,
        "Social_Media_Active": "Y",
    }
]

MOCK_COUNT_RESPONSE = {"count": 5000}

MOCK_VALIDATE_RESPONSE = {
    "valid_ids": ["CUST0001", "CUST0002"],
    "invalid_ids": [],
    "total_valid": 2,
}

MOCK_CAMPAIGN_SCHEDULE_RESPONSE = {
    "campaign_id": "abc-def-123",
    "status": "scheduled",
    "total_customers": 100,
    "scheduled_time": "2026-04-15T10:00:00Z",
}

MOCK_METRICS_RESPONSE = {
    "campaign_id": "abc-def-123",
    "total_sent": 100,
    "unique_opens": 60,
    "unique_clicks": 20,
    "open_rate": 0.6,
    "click_rate": 0.2,
    "click_through_rate": 0.3333,
}

MOCK_RESULTS_RESPONSE = [
    {
        "campaign_id": "abc-def-123",
        "customer_id": "CUST0001",
        "opened": True,
        "clicked": False,
        "open_probability": 0.45,
        "click_probability": 0.18,
    },
    {
        "campaign_id": "abc-def-123",
        "customer_id": "CUST0002",
        "opened": False,
        "clicked": False,
        "open_probability": 0.12,
        "click_probability": 0.04,
    },
]


# ── Fixtures ────────────────────────────────────────────────────────────────


def _make_response(json_data: Any, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


# ── MockCampaignClient — customer fetch ─────────────────────────────────────


def test_mock_api_client_customer_fetch():
    client = MockCampaignClient()
    with patch.object(client._session, "request", return_value=_make_response(MOCK_CUSTOMER_RESPONSE)):
        result = client.get_customers(limit=1, offset=0)
    assert len(result) == 1
    assert result[0]["customer_id"] == "CUST0001"


def test_mock_api_client_customer_count():
    client = MockCampaignClient()
    with patch.object(client._session, "request", return_value=_make_response(MOCK_COUNT_RESPONSE)):
        count = client.get_customer_count()
    assert count == 5000


def test_mock_api_client_customer_count_wrapped():
    """API may return just an integer."""
    client = MockCampaignClient()
    with patch.object(client._session, "request", return_value=_make_response(42)):
        count = client.get_customer_count()
    assert count == 42


# ── MockCampaignClient — customer validation ────────────────────────────────


def test_mock_api_client_validation():
    client = MockCampaignClient()
    with patch.object(client._session, "request", return_value=_make_response(MOCK_VALIDATE_RESPONSE)):
        result = client.validate_customer_ids(["CUST0001", "CUST0002"])
    assert result["valid_ids"] == ["CUST0001", "CUST0002"]
    assert result["total_valid"] == 2


def test_mock_api_client_validation_empty_raises():
    client = MockCampaignClient()
    with pytest.raises(MockCampaignAPIError) as exc_info:
        client.validate_customer_ids([])
    assert exc_info.value.status_code == 400


# ── MockCampaignClient — campaign schedule ───────────────────────────────────


def test_mock_api_client_campaign_schedule():
    client = MockCampaignClient()
    with patch.object(client._session, "request", return_value=_make_response(MOCK_CAMPAIGN_SCHEDULE_RESPONSE)):
        result = client.schedule_campaign(
            customer_ids=["CUST0001"],
            subject="Test Subject 40 Chars Long Now!!",
            body="<p>Test body content for the email campaign.</p>",
            scheduled_time="2026-04-15T10:00:00Z",
            segment_name="young_active",
            variant_id="var-001",
        )
    assert result["campaign_id"] == "abc-def-123"
    assert result["status"] == "scheduled"


def test_mock_api_client_campaign_schedule_with_datetime():
    client = MockCampaignClient()
    with patch.object(client._session, "request", return_value=_make_response(MOCK_CAMPAIGN_SCHEDULE_RESPONSE)):
        result = client.schedule_campaign(
            customer_ids=["CUST0001"],
            subject="Test Subject",
            body="<p>Body</p>",
            scheduled_time=datetime(2026, 4, 15, 10, 0, tzinfo=timezone.utc),
            segment_name="seg",
            variant_id="var-001",
        )
    assert result["campaign_id"] == "abc-def-123"


# ── MockCampaignClient — metrics fetch ──────────────────────────────────────


def test_mock_api_client_metrics_fetch():
    client = MockCampaignClient()
    with patch.object(client._session, "request", return_value=_make_response(MOCK_METRICS_RESPONSE)):
        result = client.get_campaign_metrics("abc-def-123")
    assert result["open_rate"] == 0.6
    assert result["click_rate"] == 0.2
    assert result["total_sent"] == 100


def test_mock_api_client_results_fetch():
    client = MockCampaignClient()
    with patch.object(client._session, "request", return_value=_make_response(MOCK_RESULTS_RESPONSE)):
        results = client.get_campaign_results("abc-def-123", limit=10)
    assert len(results) == 2
    assert results[0]["opened"] is True
    assert results[1]["opened"] is False


# ── MockCampaignClient — response parsing ───────────────────────────────────


def test_mock_api_response_parsing_wrapped_customers():
    """API may wrap customers in a dict."""
    client = MockCampaignClient()
    wrapped = {"customers": MOCK_CUSTOMER_RESPONSE}
    with patch.object(client._session, "request", return_value=_make_response(wrapped)):
        result = client.get_customers(limit=1)
    assert len(result) == 1


def test_mock_api_response_parsing_wrapped_results():
    """API may wrap results in a dict."""
    client = MockCampaignClient()
    wrapped = {"results": MOCK_RESULTS_RESPONSE}
    with patch.object(client._session, "request", return_value=_make_response(wrapped)):
        results = client.get_campaign_results("abc-def-123")
    assert len(results) == 2


# ── Error handling ───────────────────────────────────────────────────────────


def test_mock_api_400_raises_without_retry():
    """400 errors should not be retried."""
    client = MockCampaignClient()
    err_resp = MagicMock()
    err_resp.status_code = 400
    err_resp.json.return_value = {"detail": "Invalid customer IDs"}
    err_resp.raise_for_status = MagicMock()

    call_count = {"n": 0}

    def fake_request(*args, **kwargs):
        call_count["n"] += 1
        return err_resp

    with patch.object(client._session, "request", side_effect=fake_request):
        with pytest.raises(MockCampaignAPIError) as exc_info:
            client.get_campaign_metrics("bad-id")
    assert exc_info.value.status_code == 400
    assert call_count["n"] == 1  # no retry


def test_mock_api_timeout_retry(monkeypatch):
    """Timeouts should be retried up to MAX_RETRIES times."""
    client = MockCampaignClient()
    call_count = {"n": 0}

    def fake_request(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise requests.exceptions.Timeout("timed out")
        return _make_response(MOCK_COUNT_RESPONSE)

    monkeypatch.setattr("time.sleep", lambda s: None)
    with patch.object(client._session, "request", side_effect=fake_request):
        count = client.get_customer_count()
    assert count == 5000
    assert call_count["n"] == 3


def test_mock_api_network_error_retry(monkeypatch):
    """Network errors should be retried with exponential backoff."""
    client = MockCampaignClient()
    call_count = {"n": 0}

    def fake_request(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise requests.exceptions.ConnectionError("connection failed")
        return _make_response(MOCK_COUNT_RESPONSE)

    monkeypatch.setattr("time.sleep", lambda s: None)
    with patch.object(client._session, "request", side_effect=fake_request):
        count = client.get_customer_count()
    assert count == 5000
    assert call_count["n"] == 2


def test_mock_api_all_retries_exhausted(monkeypatch):
    """After all retries, the last exception is raised."""
    client = MockCampaignClient(timeout=1)

    monkeypatch.setattr("time.sleep", lambda s: None)
    with patch.object(
        client._session,
        "request",
        side_effect=requests.exceptions.Timeout("always timeout"),
    ):
        with pytest.raises(requests.exceptions.Timeout):
            client.get_customer_count()


# ── Integration of Mock API with campaign_graph fetch_customers_node ─────────


@pytest.mark.asyncio
async def test_fetch_customers_node_uses_mock_api(mock_db, monkeypatch):
    """fetch_customers_node should call Mock API and update state."""
    from app.orchestration import campaign_graph as cg
    from app.orchestration.state import create_initial_campaign_state

    monkeypatch.setattr(cg.MongoDB, "get_db", classmethod(lambda cls: mock_db))

    mock_client = MagicMock()
    mock_client.get_customer_count.return_value = 1
    mock_client.get_customers.return_value = MOCK_CUSTOMER_RESPONSE

    monkeypatch.setattr(cg, "MockCampaignClient", lambda: mock_client)

    state = create_initial_campaign_state("camp-fetch-001", "Test brief")
    result = await cg.fetch_customers_node(state)

    assert result["customer_count"] == 1
    assert len(result["customers"]) == 1
    assert result["customers"][0]["customer_id"] == "CUST0001"


@pytest.mark.asyncio
async def test_fetch_customers_node_falls_back_to_db_on_api_failure(mock_db, monkeypatch, sample_customers):
    """If Mock API fails, fetch_customers_node should use MongoDB cache."""
    from app.orchestration import campaign_graph as cg
    from app.orchestration.state import create_initial_campaign_state

    monkeypatch.setattr(cg.MongoDB, "get_db", classmethod(lambda cls: mock_db))

    for customer in sample_customers:
        await mock_db["customers"].insert_one(customer.model_dump())

    mock_client = MagicMock()
    mock_client.get_customer_count.side_effect = requests.exceptions.Timeout("cold start")

    monkeypatch.setattr(cg, "MockCampaignClient", lambda: mock_client)

    state = create_initial_campaign_state("camp-fetch-002", "Test brief")
    result = await cg.fetch_customers_node(state)

    # Falls back to DB — customers from seed data
    assert len(result["customers"]) == len(sample_customers)
    assert result["mock_api_errors"]


@pytest.mark.asyncio
async def test_mock_api_campaign_id_mapping(mock_db, monkeypatch):
    """execution_node should store mock_api_campaign_ids in state and MongoDB."""
    from app.orchestration import campaign_graph as cg
    from app.orchestration.state import create_initial_campaign_state, StateManager

    monkeypatch.setattr(cg.MongoDB, "get_db", classmethod(lambda cls: mock_db))

    def _fake_execute_campaign(self, cid, variants):
        return {
            "execution_status": "completed",
            "mock_api_campaign_ids": {"var-001": "mock-uuid-001"},
            "metrics": {"emails_scheduled": 1, "errors": []},
        }

    def fake_loader(module_name, class_name):
        if class_name == "ExecutionAgent":
            return type(
                "FakeExecutionAgent",
                (),
                {"execute_campaign": _fake_execute_campaign},
            )
        return None

    monkeypatch.setattr(cg, "_load_optional_agent", fake_loader)

    # Insert a campaign record for update_status
    await mock_db["campaigns"].insert_one({
        "campaign_id": "camp-exec-001",
        "status": "approved",
        "campaign_brief": "Test",
        "parsed_data": {},
        "created_by": "test",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "segments": [],
    })

    state = create_initial_campaign_state("camp-exec-001", "Test brief")
    state["approval_status"] = "approved"
    state["variants"] = [{"variant_id": "var-001", "customer_ids": ["CUST0001"], "segment_name": "seg"}]

    result = await cg.execution_node(state)
    assert result["mock_api_campaign_ids"].get("var-001") == "mock-uuid-001"
    assert result["execution_status"] == "completed"
