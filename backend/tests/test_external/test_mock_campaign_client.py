"""Tests for MockCampaignClient — uses 'responses' library to mock HTTP."""

from __future__ import annotations

import json

import pytest
import responses as resp_lib
import requests

from app.external.mock_campaign_client import (
    BASE_URL,
    MockCampaignAPIError,
    MockCampaignClient,
)

CLIENT = MockCampaignClient(base_url=BASE_URL, timeout=5)


# ── helpers ───────────────────────────────────────────────────────────────────

def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _json_body(data) -> str:
    return json.dumps(data)


# ── health_check ──────────────────────────────────────────────────────────────

@resp_lib.activate
def test_health_check_ok():
    resp_lib.add(resp_lib.GET, _url("/"), json={"status": "ok"}, status=200)
    result = CLIENT.health_check()
    assert result["status"] == "ok"
    assert "latency_ms" in result


@resp_lib.activate
def test_health_check_timeout_returns_error():
    resp_lib.add(resp_lib.GET, _url("/"), body=requests.exceptions.Timeout())
    result = CLIENT.health_check()
    assert result["status"] == "error"
    assert "detail" in result


# ── get_customers ─────────────────────────────────────────────────────────────

@resp_lib.activate
def test_get_customers_returns_list():
    customers = [{"customer_id": f"CUST{i:04d}"} for i in range(3)]
    resp_lib.add(resp_lib.GET, _url("/api/customers"), json=customers, status=200)
    result = CLIENT.get_customers(limit=3, offset=0)
    assert isinstance(result, list)
    assert len(result) == 3


@resp_lib.activate
def test_get_customers_unwraps_nested_dict():
    payload = {"customers": [{"customer_id": "CUST0001"}]}
    resp_lib.add(resp_lib.GET, _url("/api/customers"), json=payload, status=200)
    result = CLIENT.get_customers()
    assert result[0]["customer_id"] == "CUST0001"


@resp_lib.activate
def test_get_customers_raises_on_400():
    resp_lib.add(resp_lib.GET, _url("/api/customers"), json={"detail": "bad request"}, status=400)
    with pytest.raises(MockCampaignAPIError) as exc_info:
        CLIENT.get_customers()
    assert exc_info.value.status_code == 400


# ── get_customer_count ────────────────────────────────────────────────────────

@resp_lib.activate
def test_get_customer_count_dict_response():
    resp_lib.add(resp_lib.GET, _url("/api/customers/count"), json={"count": 5000}, status=200)
    assert CLIENT.get_customer_count() == 5000


@resp_lib.activate
def test_get_customer_count_total_key():
    resp_lib.add(resp_lib.GET, _url("/api/customers/count"), json={"total": 4999}, status=200)
    assert CLIENT.get_customer_count() == 4999


@resp_lib.activate
def test_get_customer_count_plain_int():
    resp_lib.add(resp_lib.GET, _url("/api/customers/count"), json=5000, status=200)
    assert CLIENT.get_customer_count() == 5000


# ── validate_customer_ids ─────────────────────────────────────────────────────

@resp_lib.activate
def test_validate_customer_ids_success():
    resp_lib.add(
        resp_lib.POST,
        _url("/api/customers/validate"),
        json={"valid_ids": ["CUST0001"], "invalid_ids": [], "total_valid": 1},
        status=200,
    )
    result = CLIENT.validate_customer_ids(["CUST0001"])
    assert result["total_valid"] == 1


def test_validate_customer_ids_empty_list_raises():
    with pytest.raises(MockCampaignAPIError):
        CLIENT.validate_customer_ids([])


# ── schedule_campaign ─────────────────────────────────────────────────────────

@resp_lib.activate
def test_schedule_campaign_returns_campaign_id():
    resp_lib.add(
        resp_lib.POST,
        _url("/api/campaigns/schedule"),
        json={"campaign_id": "mock-uuid-001", "status": "scheduled", "total_customers": 1},
        status=200,
    )
    result = CLIENT.schedule_campaign(
        customer_ids=["CUST0001"],
        subject="Test subject",
        body="Test body content",
        scheduled_time="2026-06-01T10:00:00Z",
        segment_name="test_segment",
        variant_id="variant_001",
    )
    assert result["campaign_id"] == "mock-uuid-001"


@resp_lib.activate
def test_schedule_campaign_raises_on_400():
    resp_lib.add(
        resp_lib.POST,
        _url("/api/campaigns/schedule"),
        json={"detail": "invalid payload"},
        status=400,
    )
    with pytest.raises(MockCampaignAPIError) as exc_info:
        CLIENT.schedule_campaign(
            customer_ids=["CUST0001"],
            subject="s",
            body="b",
            scheduled_time="2026-06-01T10:00:00Z",
            segment_name="seg",
            variant_id="vid",
        )
    assert exc_info.value.status_code == 400


# ── get_campaign_metrics ──────────────────────────────────────────────────────

@resp_lib.activate
def test_get_campaign_metrics_returns_rates():
    resp_lib.add(
        resp_lib.GET,
        _url("/api/campaigns/mock-id-001/metrics"),
        json={
            "campaign_id": "mock-id-001",
            "open_rate": 0.35,
            "click_rate": 0.085,
            "click_through_rate": 0.06,
            "total_sent": 1000,
            "unique_opens": 350,
            "unique_clicks": 85,
        },
        status=200,
    )
    result = CLIENT.get_campaign_metrics("mock-id-001")
    assert result["open_rate"] == 0.35
    assert result["total_sent"] == 1000


@resp_lib.activate
def test_get_campaign_metrics_404_raises():
    resp_lib.add(resp_lib.GET, _url("/api/campaigns/ghost/metrics"), json={"detail": "not found"}, status=404)
    with pytest.raises(MockCampaignAPIError) as exc_info:
        CLIENT.get_campaign_metrics("ghost")
    assert exc_info.value.status_code == 404


# ── get_campaign_results ──────────────────────────────────────────────────────

@resp_lib.activate
def test_get_campaign_results_returns_list():
    results = [{"customer_id": "CUST0001", "opened": True, "clicked": False}]
    resp_lib.add(
        resp_lib.GET,
        _url("/api/campaigns/mock-id-001/results"),
        json=results,
        status=200,
    )
    data = CLIENT.get_campaign_results("mock-id-001")
    assert isinstance(data, list)
    assert data[0]["customer_id"] == "CUST0001"


# ── validators ────────────────────────────────────────────────────────────────

def test_validate_campaign_response_ok():
    MockCampaignClient._validate_campaign_response({"campaign_id": "abc", "status": "scheduled"})


def test_validate_campaign_response_missing_field():
    with pytest.raises(ValueError):
        MockCampaignClient._validate_campaign_response({"status": "scheduled"})


def test_validate_campaign_response_empty_id():
    with pytest.raises(ValueError):
        MockCampaignClient._validate_campaign_response({"campaign_id": "", "status": "scheduled"})


def test_validate_metrics_response_ok():
    MockCampaignClient._validate_metrics_response(
        {"open_rate": 0.3, "click_rate": 0.1, "click_through_rate": 0.05}
    )


def test_validate_metrics_response_missing_field():
    with pytest.raises(ValueError):
        MockCampaignClient._validate_metrics_response({"open_rate": 0.3, "click_rate": 0.1})


def test_validate_metrics_response_out_of_range():
    with pytest.raises(ValueError):
        MockCampaignClient._validate_metrics_response(
            {"open_rate": 1.5, "click_rate": 0.1, "click_through_rate": 0.05}
        )


def test_validate_customer_data_ok():
    MockCampaignClient._validate_customer_data({"customer_id": "CUST0001", "email": "a@b.com"})


def test_validate_customer_data_missing_id():
    with pytest.raises(ValueError):
        MockCampaignClient._validate_customer_data({"email": "a@b.com"})


def test_validate_customer_data_bad_format():
    with pytest.raises(ValueError):
        MockCampaignClient._validate_customer_data({"customer_id": "USER123"})
