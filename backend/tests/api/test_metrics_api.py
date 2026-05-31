"""API tests for /metrics endpoints."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestMetricsAPI:

    def test_list_metrics_returns_200(self, client):
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200

    def test_list_metrics_pagination(self, client):
        response = client.get("/api/v1/metrics?skip=0&limit=5")
        assert response.status_code == 200

    def test_get_campaign_metrics_unknown_campaign(self, client):
        response = client.get("/api/v1/metrics/campaign/unknown-camp")
        assert response.status_code in (200, 404)

    def test_get_campaign_metrics_returns_list(self, client):
        # Create campaign first
        create = client.post(
            "/api/v1/campaigns", json={"campaign_brief": "Test campaign for metrics API."}
        )
        camp_id = create.json().get("campaign_id") or create.json().get("id")

        response = client.get(f"/api/v1/metrics/campaign/{camp_id}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_metrics_aggregates_unknown_campaign(self, client):
        response = client.get("/api/v1/metrics/campaign/unknown-camp/aggregates")
        assert response.status_code in (200, 404)

    def test_get_metrics_distribution_unknown_campaign(self, client):
        response = client.get("/api/v1/metrics/campaign/unknown-camp/distribution")
        assert response.status_code in (200, 404)

    def test_top_performers_returns_200(self, client):
        response = client.get("/api/v1/metrics/top-performers")
        assert response.status_code == 200

    def test_top_performers_with_limit(self, client):
        response = client.get("/api/v1/metrics/top-performers?limit=3")
        assert response.status_code == 200

    def test_get_metric_by_id_not_found(self, client):
        response = client.get("/api/v1/metrics/nonexistent-metric-id")
        assert response.status_code == 404

    def test_create_metrics_record(self, client):
        payload = {
            "campaign_id": "camp-test-001",
            "variant_id": "var-test-001",
            "mock_campaign_id": "mock-test-001",
            "open_rate": 0.35,
            "click_rate": 0.08,
            "click_through_rate": 0.06,
            "total_sent": 1000,
            "unique_opens": 350,
            "unique_clicks": 80,
        }
        response = client.post("/api/v1/metrics", json=payload)
        assert response.status_code in (200, 201)
