"""End-to-end tests: optimization service and A/B testing full loop."""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.api.deps import get_database, get_mock_api_client
from app.db.mongodb import MongoDB
from app.main import app

BRIEF = "Promote XDeposit savings — optimization E2E full loop test."


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def opt_client():
    mock_db = AsyncMongoMockClient()["campaignx_opt_e2e"]
    mock_api = MagicMock()
    mock_api.health_check.return_value = {"status": "ok", "latency_ms": 5.0}

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
class TestOptimizationE2E:
    _campaign_id: str = ""
    _ab_test_id: str = ""

    def test_01_create_campaign_for_optimization(self, opt_client):
        resp = opt_client.post("/api/v1/campaigns", json={"campaign_brief": BRIEF})
        assert resp.status_code == 201
        TestOptimizationE2E._campaign_id = resp.json().get("campaign_id") or resp.json().get("id")

    def test_02_optimization_status_initially_accessible(self, opt_client):
        camp_id = TestOptimizationE2E._campaign_id
        resp = opt_client.get(f"/api/v1/optimization/{camp_id}/status")
        assert resp.status_code == 200

    def test_03_detailed_optimization_status_accessible(self, opt_client):
        camp_id = TestOptimizationE2E._campaign_id
        resp = opt_client.get(
            f"/api/v1/optimization/campaigns/{camp_id}/optimization-status"
        )
        assert resp.status_code == 200

    def test_04_optimization_history_is_empty_initially(self, opt_client):
        camp_id = TestOptimizationE2E._campaign_id
        resp = opt_client.get(
            f"/api/v1/optimization/campaigns/{camp_id}/optimization-history"
        )
        assert resp.status_code == 200
        body = resp.json()
        iterations = body.get("iterations", body.get("items", []))
        assert isinstance(iterations, list)

    def test_05_optimization_insights_accessible(self, opt_client):
        camp_id = TestOptimizationE2E._campaign_id
        resp = opt_client.get(
            f"/api/v1/optimization/campaigns/{camp_id}/optimization-insights"
        )
        assert resp.status_code == 200

    def test_06_create_ab_test_for_campaign(self, opt_client):
        camp_id = TestOptimizationE2E._campaign_id
        resp = opt_client.post(
            f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests"
            "?variant_a_id=var-opt-a&variant_b_id=var-opt-b&test_duration_hours=12"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "test_id" in body
        TestOptimizationE2E._ab_test_id = body["test_id"]

    def test_07_get_ab_test_details(self, opt_client):
        test_id = TestOptimizationE2E._ab_test_id
        resp = opt_client.get(f"/api/v1/ab-tests/{test_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["test_id"] == test_id

    def test_08_ab_test_recommendation_accessible(self, opt_client):
        test_id = TestOptimizationE2E._ab_test_id
        resp = opt_client.get(f"/api/v1/ab-tests/{test_id}/recommendation")
        assert resp.status_code == 200
        body = resp.json()
        assert "recommendation" in body or "winner" in body

    def test_09_ab_tests_listed_for_campaign(self, opt_client):
        camp_id = TestOptimizationE2E._campaign_id
        resp = opt_client.get(f"/api/v1/ab-tests/campaigns/{camp_id}/ab-tests")
        assert resp.status_code == 200
        body = resp.json()
        tests = body.get("tests", body.get("items", body if isinstance(body, list) else []))
        assert isinstance(tests, list)
        assert len(tests) >= 1

    def test_10_variant_iterations_history_accessible(self, opt_client):
        camp_id = TestOptimizationE2E._campaign_id
        resp = opt_client.get(
            f"/api/v1/variant-iterations/variants/var-opt-a/iteration-history"
            f"?campaign_id={camp_id}"
        )
        assert resp.status_code == 200

    def test_11_analytics_reflect_campaign_state(self, opt_client):
        camp_id = TestOptimizationE2E._campaign_id
        resp = opt_client.get(f"/api/v1/analytics/campaigns/{camp_id}/analytics")
        assert resp.status_code == 200

    def test_12_dashboard_reflects_campaign(self, opt_client):
        camp_id = TestOptimizationE2E._campaign_id
        resp = opt_client.get(f"/api/v1/dashboard/campaign/{camp_id}")
        assert resp.status_code == 200
