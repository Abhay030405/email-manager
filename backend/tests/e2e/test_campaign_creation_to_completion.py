"""End-to-end tests: campaign creation through approval flow."""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.api.deps import get_database, get_mock_api_client
from app.db.mongodb import MongoDB
from app.main import app

BRIEF = (
    "Promote XDeposit high-yield savings account to young urban professionals aged 25-35 "
    "in Mumbai and Delhi. Goal: drive 15% conversion. Budget: ₹5,00,000."
)


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def e2e_client():
    """Module-scoped TestClient that persists state across tests in this module."""
    mock_db = AsyncMongoMockClient()["campaignx_e2e"]

    mock_api = MagicMock()
    mock_api.get_campaign_metrics.return_value = {
        "campaign_id": "mock-e2e-001",
        "open_rate": 0.38,
        "click_rate": 0.09,
        "click_through_rate": 0.07,
        "total_sent": 500,
        "unique_opens": 190,
        "unique_clicks": 45,
    }
    mock_api.get_campaign_results.return_value = [
        {"customer_id": "CUST0001", "opened": True, "clicked": True,
         "open_probability": 0.8, "click_probability": 0.5},
        {"customer_id": "CUST0002", "opened": True, "clicked": False,
         "open_probability": 0.6, "click_probability": 0.2},
        {"customer_id": "CUST0003", "opened": False, "clicked": False,
         "open_probability": 0.2, "click_probability": 0.05},
    ]
    mock_api.schedule_campaign.return_value = {
        "campaign_id": "mock-e2e-001",
        "status": "scheduled",
        "total_customers": 3,
    }
    mock_api.health_check.return_value = {"status": "ok", "latency_ms": 8.0}

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_database] = _override_db
    app.dependency_overrides[get_mock_api_client] = lambda: mock_api

    with ExitStack() as stack:
        stack.enter_context(patch.object(MongoDB, "get_db", return_value=mock_db))
        tc = TestClient(app, raise_server_exceptions=True)
        yield tc

    app.dependency_overrides.clear()


@pytest.mark.e2e
class TestCampaignE2E:
    """Full campaign lifecycle: create → read → update → delete."""

    _campaign_id: str = ""

    def test_01_create_campaign(self, e2e_client):
        response = e2e_client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
        assert response.status_code == 201
        body = response.json()
        TestCampaignE2E._campaign_id = body.get("campaign_id") or body.get("id")
        assert TestCampaignE2E._campaign_id

    def test_02_get_created_campaign(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.get(f"/api/v1/campaigns/{camp_id}")
        assert response.status_code == 200
        body = response.json()
        assert (body.get("campaign_id") or body.get("id")) == camp_id

    def test_03_campaign_appears_in_list(self, e2e_client):
        response = e2e_client.get("/api/v1/campaigns")
        assert response.status_code == 200
        body = response.json()
        items = body.get("items") or body.get("campaigns") or body
        if isinstance(items, list):
            ids = [
                (c.get("campaign_id") or c.get("id")) for c in items
            ]
            assert TestCampaignE2E._campaign_id in ids

    def test_04_update_campaign_brief(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.patch(
            f"/api/v1/campaigns/{camp_id}",
            json={"campaign_brief": BRIEF + " [Updated]"},
        )
        assert response.status_code == 200

    def test_05_workflow_status_accessible(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.get(f"/api/v1/campaigns/{camp_id}/workflow-status")
        assert response.status_code == 200

    def test_06_optimization_status_accessible(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.get(f"/api/v1/optimization/{camp_id}/status")
        assert response.status_code == 200

    def test_07_metrics_for_campaign_accessible(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.get(f"/api/v1/metrics/campaign/{camp_id}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_08_analytics_accessible(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.get(f"/api/v1/analytics/campaigns/{camp_id}/analytics")
        assert response.status_code == 200

    def test_09_alerts_accessible(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.get(f"/api/v1/alerts/campaign/{camp_id}")
        assert response.status_code == 200

    def test_10_dashboard_campaign_accessible(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.get(f"/api/v1/dashboard/campaign/{camp_id}")
        assert response.status_code == 200

    def test_11_create_ab_test(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.post(
            f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests"
            "?variant_a_id=var-e2e-a&variant_b_id=var-e2e-b&test_duration_hours=24"
        )
        assert response.status_code == 200
        body = response.json()
        assert "test_id" in body

    def test_12_delete_campaign(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.delete(f"/api/v1/campaigns/{camp_id}")
        assert response.status_code == 204

    def test_13_deleted_campaign_not_found(self, e2e_client):
        camp_id = TestCampaignE2E._campaign_id
        response = e2e_client.get(f"/api/v1/campaigns/{camp_id}")
        assert response.status_code == 404
