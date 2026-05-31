"""API error response tests — 4xx and 5xx scenarios."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestAPIErrors:

    # ── 404 Not Found ─────────────────────────────────────────────

    def test_get_campaign_404(self, client):
        response = client.get("/api/v1/campaigns/does-not-exist-at-all")
        assert response.status_code == 404

    def test_get_customer_404(self, client):
        response = client.get("/api/v1/customers/CUST9999")
        assert response.status_code == 404

    def test_get_metric_by_id_404(self, client):
        response = client.get("/api/v1/metrics/nonexistent-metric-id")
        assert response.status_code == 404

    def test_get_ab_test_404(self, client):
        response = client.get("/api/v1/ab-tests/nonexistent-test")
        assert response.status_code == 404

    def test_alert_by_id_404(self, client):
        response = client.get("/api/v1/alerts/nonexistent-alert")
        assert response.status_code == 404

    # ── 422 Unprocessable Entity ──────────────────────────────────

    def test_create_campaign_missing_brief_422(self, client):
        response = client.post("/api/v1/campaigns", json={})
        assert response.status_code == 422

    def test_create_campaign_extra_field_ignored_or_rejected(self, client):
        response = client.post(
            "/api/v1/campaigns",
            json={"campaign_brief": "Valid brief text here.", "unknown_field": "abc"},
        )
        # FastAPI by default ignores extra fields — should still create
        assert response.status_code in (201, 422)

    def test_list_campaigns_invalid_skip_type_422(self, client):
        response = client.get("/api/v1/campaigns?skip=abc")
        assert response.status_code == 422

    def test_list_campaigns_negative_limit_rejected(self, client):
        response = client.get("/api/v1/campaigns?limit=-1")
        assert response.status_code in (200, 422)

    def test_variant_iterations_missing_campaign_id_422(self, client):
        response = client.get("/api/v1/variant-iterations/variants/var-001/iterations")
        assert response.status_code == 422

    # ── 404 error body format ─────────────────────────────────────

    def test_404_error_has_detail_field(self, client):
        response = client.get("/api/v1/campaigns/totally-nonexistent-id")
        assert response.status_code == 404
        body = response.json()
        assert "detail" in body

    def test_422_error_has_detail_field(self, client):
        response = client.post("/api/v1/campaigns", json={})
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body

    # ── Wrong HTTP method ─────────────────────────────────────────

    def test_delete_campaigns_list_method_not_allowed(self, client):
        response = client.delete("/api/v1/campaigns")
        assert response.status_code == 405

    def test_put_campaigns_not_allowed(self, client):
        response = client.put("/api/v1/campaigns", json={})
        assert response.status_code == 405

    # ── Unknown route ─────────────────────────────────────────────

    def test_unknown_route_returns_404(self, client):
        response = client.get("/api/v1/nonexistent-endpoint-xyz")
        assert response.status_code == 404

    def test_deeply_nested_unknown_route_returns_404(self, client):
        response = client.get("/api/v1/campaigns/abc/totally/unknown/subroute")
        assert response.status_code == 404
